/*
 *  pp_psc_delta.cpp
 *
 *  This file is part of NEST.
 *
 *  Copyright (C) 2004 The NEST Initiative
 *
 *  NEST is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  NEST is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with NEST.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

/*
 *  Multimeter support by Yury V. Zaytsev.
 */

/* pp_psc_delta is a stochastically spiking neuron where the potential jumps on each spike arrival. */

#include "exceptions.h"
#include "pp_psc_delta.h"
#include "network.h"
#include "dict.h"
#include "integerdatum.h"
#include "doubledatum.h"
#include "dictutils.h"
#include "numerics.h"
#include "universal_data_logger_impl.h"

#include <limits>

namespace nest
{
  /* ----------------------------------------------------------------
   * Recordables map
   * ---------------------------------------------------------------- */

  RecordablesMap<pp_psc_delta> pp_psc_delta::recordablesMap_;

  // Override the create() method with one call to RecordablesMap::insert_()
  // for each quantity to be recorded.
  template <>
  void RecordablesMap<pp_psc_delta>::create()
  {
    // use standard names whereever you can for consistency!
    insert_(names::V_m, &pp_psc_delta::get_V_m_);
    insert_(names::E_sfa, &pp_psc_delta::get_E_sfa_);
  }

/* ----------------------------------------------------------------
 * Default constructors defining default parameters and state
 * ---------------------------------------------------------------- */

nest::pp_psc_delta::Parameters_::Parameters_()
  : tau_m_            (  10.0    ),  // ms
    c_m_              ( 250.0    ),  // pF
    dead_time_        (   1.0    ),  // ms
    dead_time_random_ (    0     ),
    dead_time_shape_  (    1     ),
    with_reset_       (    1     ),
    tau_sfa_          (  34.0    ),  // ms
    q_sfa_            (   0.0    ),  // mV, reasonable default is 7 mV [2]
    c_1_              (   0.0    ),  // Hz / mV
    c_2_              (   1.238  ),  // Hz / mV
    c_3_              (   0.25   ),  // 1.0 / mV
    I_e_              (   0.0    ),  // pA
    t_ref_remaining_  (   0.0    )   // ms
{}

nest::pp_psc_delta::State_::State_()
  : y0_   (0.0),
    y3_   (0.0),
    q_    (0.0),
    r_    (0)
{}

/* ----------------------------------------------------------------
 * Parameter and state extractions and manipulation functions
 * ---------------------------------------------------------------- */

void nest::pp_psc_delta::Parameters_::get(DictionaryDatum &d) const
{
  def<double>(d, names::I_e, I_e_);
  def<double>(d, names::C_m, c_m_);
  def<double>(d, names::tau_m, tau_m_);
  def<double>(d, names::dead_time, dead_time_);
  def<bool>(d, names::dead_time_random, dead_time_random_);
  def<long>(d, names::dead_time_shape, dead_time_shape_);
  def<bool>(d, names::with_reset, with_reset_);
  def<double>(d, names::tau_sfa, tau_sfa_);
  def<double>(d, names::q_sfa, q_sfa_);
  def<double>(d, names::c_1, c_1_);
  def<double>(d, names::c_2, c_2_);
  def<double>(d, names::c_3, c_3_);
  def<double>(d, names::t_ref_remaining, t_ref_remaining_);
}

void nest::pp_psc_delta::Parameters_::set(const DictionaryDatum& d)
{

  updateValue<double>(d, names::I_e, I_e_);
  updateValue<double>(d, names::C_m, c_m_);
  updateValue<double>(d, names::tau_m, tau_m_);
  updateValue<double>(d, names::dead_time, dead_time_);
  updateValue<bool>(d, names::dead_time_random, dead_time_random_);
  updateValue<long>(d, names::dead_time_shape, dead_time_shape_);
  updateValue<bool>(d, names::with_reset, with_reset_);
  updateValue<double>(d, names::tau_sfa, tau_sfa_);
  updateValue<double>(d, names::q_sfa, q_sfa_);
  updateValue<double>(d, names::c_1, c_1_);
  updateValue<double>(d, names::c_2, c_2_);
  updateValue<double>(d, names::c_3, c_3_);
  updateValue<double>(d, names::t_ref_remaining, t_ref_remaining_);

  if ( c_m_ <= 0 )
    throw BadProperty("Capacitance must be strictly positive.");

  if ( dead_time_ < 0 )
    throw BadProperty("Absolute refractory time must not be negative.");

  if ( dead_time_shape_ < 1 )
    throw BadProperty("Shape of the dead time gamma distribution must not be smaller than 1.");

  if ( tau_m_ <= 0 )
    throw BadProperty("All time constants must be strictly positive.");

  if ( tau_sfa_ <= 0 )
    throw BadProperty("All time constants must be strictly positive.");

  if ( t_ref_remaining_ < 0)
    throw BadProperty("Remaining refractory time can not be negative");

}

void nest::pp_psc_delta::State_::get(DictionaryDatum &d, const Parameters_&) const
{
  def<double>(d, names::V_m, y3_); // Membrane potential
  def<double>(d, names::E_sfa, q_); // Adaptive threshold potential
}

void nest::pp_psc_delta::State_::set(const DictionaryDatum& d, const Parameters_&)
{
  updateValue<double>(d, names::V_m, y3_);
  updateValue<double>(d, names::E_sfa, q_);
}

nest::pp_psc_delta::Buffers_::Buffers_(pp_psc_delta &n)
  : logger_(n)
{}

nest::pp_psc_delta::Buffers_::Buffers_(const Buffers_ &, pp_psc_delta &n)
  : logger_(n)
{}

/* ----------------------------------------------------------------
 * Default and copy constructor for node
 * ---------------------------------------------------------------- */

nest::pp_psc_delta::pp_psc_delta()
  : Archiving_Node(),
    P_(),
    S_(),
    B_(*this)
{
  recordablesMap_.create();
}

nest::pp_psc_delta::pp_psc_delta(const pp_psc_delta& n)
  : Archiving_Node(n),
    P_(n.P_),
    S_(n.S_),
    B_(n.B_, *this)
{}

/* ----------------------------------------------------------------
 * Node initialization functions
 * ---------------------------------------------------------------- */

void nest::pp_psc_delta::init_state_(const Node& proto)
{
  const pp_psc_delta& pr = downcast<pp_psc_delta>(proto);
  S_ = pr.S_;
  S_.r_ = Time(Time::ms(P_.t_ref_remaining_)).get_steps();
}

void nest::pp_psc_delta::init_buffers_()
{
  B_.spikes_.clear();           //!< includes resize
  B_.currents_.clear();         //!< includes resize
  B_.logger_.reset();           //!< includes resize
  Archiving_Node::clear_history();
}

void nest::pp_psc_delta::calibrate()
{
  B_.logger_.init();

  V_.h_ = Time::get_resolution().get_ms();
  V_.rng_ = net_->get_rng(get_thread());

  V_.P33_ = std::exp(-V_.h_/P_.tau_m_);
  V_.P30_ = 1/P_.c_m_*(1-V_.P33_)*P_.tau_m_;

  V_.Q33_ = std::exp(-V_.h_/P_.tau_sfa_);

  // TauR specifies the length of the absolute refractory period as
  // a double_t in ms. The grid based iaf_psp_delta can only handle refractory
  // periods that are integer multiples of the computation step size (h).
  // To ensure consistency with the overall simulation scheme such conversion
  // should be carried out via objects of class nest::Time. The conversion
  // requires 2 steps:
  //
  //     1. A time object r is constructed defining the representation of
  //        TauR in tics. This representation is then converted to computation time
  //        steps again by a strategy defined by class nest::Time.
  //     2. The refractory time in units of steps is read out by get_steps(), a member
  //        function of class nest::Time.
  //
  // The definition of the refractory period of the pp_psc_delta is consistent
  // with the one of iaf_neuron_ps.
  //
  // Choosing a TauR that is not an integer multiple of the computation time
  // step h will lead to accurate (up to the resolution h) and self-consistent
  // results. However, a neuron model capable of operating with real valued spike
  // time may exhibit a different effective refractory time.

  if (P_.dead_time_random_)
  {
    V_.dt_rate_ = P_.dead_time_shape_ / P_.dead_time_;  // Choose dead time rate parameter such that mean equals dead_time
    V_.gamma_dev_.set_order(P_.dead_time_shape_);
  }

  else
  {
    V_.DeadTimeCounts_ = Time(Time::ms(P_.dead_time_)).get_steps();
    assert(V_.DeadTimeCounts_ >= 0);  // Since t_ref_ >= 0, this can only fail in error
  }
}

/* ----------------------------------------------------------------
 * Update and spike handling functions
 */

void nest::pp_psc_delta::update(Time const & origin, const long_t from, const long_t to)
{
  assert(to >= 0 && (delay) from < Scheduler::get_min_delay());
  assert(from < to);

  for ( long_t lag = from ; lag < to ; ++lag )
  {

    S_.y3_ = V_.P30_*(S_.y0_ + P_.I_e_) + V_.P33_*S_.y3_ + B_.spikes_.get_value(lag);

    if (P_.q_sfa_ != 0.0)
      S_.q_ = V_.Q33_ * S_.q_;

    if ( S_.r_ == 0 )
    {
      // Neuron not refractory

      // Calculate instantaneous rate from transfer function:
      //     rate = c1 * y3' + c2 * exp(c3 * y3')
      // Adaptive threshold leads to effective potential V_eff instead of y3

      double_t V_eff;

      if (P_.q_sfa_ != 0.0)
        V_eff = S_.y3_ - S_.q_;
      else
        V_eff = S_.y3_;

      double_t rate = (P_.c_1_ * V_eff + P_.c_2_ * std::exp(P_.c_3_ * V_eff));

      if (rate > 0.0)
      {
        ulong_t n_spikes = 0;

        if (P_.dead_time_ > 0.0)
        {
          // Draw random number and compare to prob to have a spike
          if ( V_.rng_->drand() <= -numerics::expm1(-rate*V_.h_*1e-3) )
            n_spikes = 1;
        }
        else
        {
          // Draw Poisson random number of spikes
          V_.poisson_dev_.set_lambda(rate*V_.h_*1e-3);
          n_spikes = V_.poisson_dev_.uldev(V_.rng_);
        }

        if ( n_spikes > 0 ) // Is there a spike? Then set the new dead time.
        {
          // Set dead time interval according to paramters
          if (P_.dead_time_random_)
          {
            S_.r_ = Time(Time::ms(V_.gamma_dev_(V_.rng_) / V_.dt_rate_)).get_steps();
          }
          else
            S_.r_ = V_.DeadTimeCounts_;

          // Increment the adaptive threshold
          if (P_.q_sfa_ != 0.0)
            S_.q_ += P_.q_sfa_;

          // And send the spike event
          SpikeEvent se;
          se.set_multiplicity(n_spikes);
          network()->send(*this, se, lag);

          // Reset the potential if applicable
          if (P_.with_reset_)
          {
            S_.y3_ = 0.0;
          }
        } // S_.y3_ = P_.V_reset_;
      } // if (rate > 0.0)
    }
    else // Neuron is within dead time
    {
      --S_.r_;
    }

    // Set new input current
    S_.y0_ = B_.currents_.get_value(lag);

    // Voltage logging
    B_.logger_.record_data(origin.get_steps() + lag);

  }
}

void nest::pp_psc_delta::handle(SpikeEvent & e)
{
  assert(e.get_delay() > 0);

  // EX: We must compute the arrival time of the incoming spike
  //     explicitly, since it depends on delay and offset within
  //     the update cycle.  The way it is done here works, but
  //     is clumsy and should be improved.
  B_.spikes_.add_value(e.get_rel_delivery_steps(network()->get_slice_origin()),
                    e.get_weight() * e.get_multiplicity() );
}

void nest::pp_psc_delta::handle(CurrentEvent& e)
{
  assert(e.get_delay() > 0);

  const double_t c=e.get_current();
  const double_t w=e.get_weight();

  // Add weighted current; HEP 2002-10-04
  B_.currents_.add_value(e.get_rel_delivery_steps(network()->get_slice_origin()),
      w *c);
}

void nest::pp_psc_delta::handle(DataLoggingRequest &e)
{
  B_.logger_.handle(e);
}

} // namespace
