/*
 *  stdp_connection_facetshw_hom.h
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

#ifndef STDP_CONNECTION_FACETSHW_HOM_H
#define STDP_CONNECTION_FACETSHW_HOM_H

/* BeginDocumentation
  Name: stdp_facetshw_synapse_hom - Synapse type for spike-timing dependent
   plasticity using homogeneous parameters, i.e. all synapses have the same parameters.

  Description:
   stdp_facetshw_synapse is a connector to create synapses with spike-timing
   dependent plasticity (as defined in [1]).
   This connector is a modified version of stdp_synapse.
   It includes constraints of the hardware developed in the FACETS (BrainScaleS) project [2,3],
   as e.g. 4-bit weight resolution, sequential updates of groups of synapses
   and reduced symmetric nearest-neighbor spike pairing scheme. For details see [3].
   The modified spike pairing scheme requires the calculation of tau_minus_
   within this synapse and not at the neuron site via Kplus_ like in stdp_connection_hom.

  Parameters:
   Common properties:
    tau_plus        double - Time constant of STDP window, causal branch in ms 
    tau_minus_stdp  double - Time constant of STDP window, anti-causal branch in ms 
    Wmax            double - Maximum allowed weight

    no_synapses                    long - total number of synapses
    synapses_per_driver            long - number of synapses updated at once
    driver_readout_time          double - time for processing of one synapse row (synapse line driver)
    readout_cycle_duration       double - duration between two subsequent updates of same synapse (synapse line driver)
    lookuptable_0          vector<long> - three look-up tables (LUT)
    lookuptable_1          vector<long>
    lookuptable_2          vector<long>
    configbit_0            vector<long> - configuration bits for evaluation function.
                                          For details see code in function eval_function_ and [4]
                                          (configbit[0]=e_cc, ..[1]=e_ca, ..[2]=e_ac, ..[3]=e_aa).
                                          Depending on these two sets of configuration bits
                                          weights are updated according LUTs (out of three: (1,0), (0,1), (1,1)).
                                          For (0,0) continue without reset.
    configbit_1            vector<long>
    reset_pattern          vector<long> - configuration bits for reset behaviour.
                                          Two bits for each LUT (reset causal and acausal).
                                          In hardware only (all false; never reset)
                                          or (all true; always reset) is allowed.

   Individual properties:
    a_causal     double - causal and anti-causal spike pair accumulations
    a_acausal    double
    a_thresh_th  double - two thresholds used in evaluation function.
                          No common property, because variation of analog synapse circuitry can be applied here
    a_thresh_tl  double
    synapse_id   long   - synapse ID, used to assign synapses to groups (synapse drivers)

  Notes:
   The synapse IDs are assigned to each synapse in an ascending order (0,1,2, ...) according their first
   presynaptic activity and is used to group synapses that are updated at once.
   It is possible to avoid activity dependent synapse ID assignments by manually setting the no_synapses
   and the synapse_id(s) before running the simulation.
   The weights will be discretized after the first presynaptic activity at a synapse.

  Transmits: SpikeEvent
   
  References:
   [1] Morrison, A., Diesmann, M., and Gerstner, W. (2008).
       Phenomenological models of synaptic plasticity based on
       spike-timing, Biol. Cybern., 98,459--478

   [2] Schemmel, J., Gruebl, A., Meier, K., and Mueller, E. (2006).
       Implementing synaptic plasticity in a VLSI spiking neural
       network model, In Proceedings of the 2006 International
       Joint Conference on Neural Networks, pp.1--6, IEEE Press

   [3] Pfeil, T., Potjans, T. C., Schrader, S., Potjans, W., Schemmel, J., Diesmann, M., & Meier, K. (2012).
       Is a 4-bit synaptic weight resolution enough? - 
       constraints on enabling spike-timing dependent plasticity in neuromorphic hardware.
       Front. Neurosci. 6 (90).

   [4] Friedmann, S. in preparation


  FirstVersion: July 2011
  Author: Thomas Pfeil (TP), Moritz Helias, Abigail Morrison
  SeeAlso: stdp_synapse, synapsedict, tsodyks_synapse, static_synapse
*/

#include "connection_het_wd.h"
#include "archiving_node.h"
#include <cmath>

namespace nest
{

  /**
   * Class containing the common properties for all synapses of type STDPFACETSHWConnectionHom.
   */
  class STDPFACETSHWHomCommonProperties : public CommonSynapseProperties
    {
      friend class STDPFACETSHWConnectionHom;

    public:

      /**
       * Default constructor.
       * Sets all property values to defaults.
       */
      STDPFACETSHWHomCommonProperties();

      /**
       * Get all properties and put them into a dictionary.
       */
      void get_status(DictionaryDatum & d) const;

      /**
       * Set properties from the values given in dictionary.
       */
      void set_status(const DictionaryDatum & d, ConnectorModel& cm);

      // overloaded for all supported event types
      void check_event(SpikeEvent&) {}

    private:
      /**
       * Calculate the readout cycle duration
       */
      void calc_readout_cycle_duration_();


      // data members common to all connections
      double_t tau_plus_;
      double_t tau_minus_;
      double_t Wmax_;
      double_t weight_per_lut_entry_;

      //STDP controller parameters
      long_t no_synapses_;
      long_t synapses_per_driver_;
      double_t driver_readout_time_;
      double_t readout_cycle_duration_;
      std::vector<long_t> lookuptable_0_; //TODO: TP: size in memory could be reduced
      std::vector<long_t> lookuptable_1_;
      std::vector<long_t> lookuptable_2_; //TODO: TP: to save memory one could introduce vector<bool> & BoolVectorDatum
      std::vector<long_t> configbit_0_;
      std::vector<long_t> configbit_1_;
      std::vector<long_t> reset_pattern_;
    };



  /**
   * Class representing an STDP connection with homogeneous parameters, i.e. parameters are the same for all synapses.
   */
  class STDPFACETSHWConnectionHom : public ConnectionHetWD
  {

  public:
  /**
   * Default Constructor.
   * Sets default values for all parameters. Needed by GenericConnectorModel.
   */
  STDPFACETSHWConnectionHom();

  /**
   * Copy constructor from a property object.
   * Needs to be defined properly in order for GenericConnector to work.
   */
  STDPFACETSHWConnectionHom(const STDPFACETSHWConnectionHom &);

  /**
   * Default Destructor.
   */
  virtual ~STDPFACETSHWConnectionHom() {}

  /*
   * This function calls check_connection on the sender and checks if the receiver
   * accepts the event type and receptor type requested by the sender.
   * Node::check_connection() will either confirm the receiver port by returning
   * true or false if the connection should be ignored.
   * We have to override the base class' implementation, since for STDP
   * connections we have to call register_stdp_connection on the target neuron
   * to inform the Archiver to collect spikes for this connection.
   *
   * \param s The source node
   * \param r The target node
   * \param receptor_type The ID of the requested receptor type
   * \param t_lastspike last spike produced by presynaptic neuron (in ms)
   */
  void check_connection(Node & s, Node & r, rport receptor_type, double_t t_lastspike);

  /**
   * Get all properties of this connection and put them into a dictionary.
   */
  void get_status(DictionaryDatum & d) const;

  /**
   * Set properties of this connection from the values given in dictionary.
   */
  void set_status(const DictionaryDatum & d, ConnectorModel &cm);

  /**
   * Set properties of this connection from position p in the properties
   * array given in dictionary.
   */
  void set_status(const DictionaryDatum & d, index p, ConnectorModel &cm);

  /**
   * Create new empty arrays for the properties of this connection in the given
   * dictionary. It is assumed that they are not existing before.
   */
  void initialize_property_arrays(DictionaryDatum & d) const;

  /**
   * Append properties of this connection to the given dictionary. If the
   * dictionary is empty, new arrays are created first.
   */
  void append_properties(DictionaryDatum & d) const;

  /**
   * Send an event to the receiver of this connection.
   * \param e The event to send
   * \param t_lastspike Point in time of last spike sent.
   */
  void send(Event& e, double_t t_lastspike, STDPFACETSHWHomCommonProperties &);

  // overloaded for all supported event types
  using Connection::check_event;
  void check_event(SpikeEvent&) {}

 private:
  bool eval_function_(double_t a_causal, double_t a_acausal, double_t a_thresh_th, double_t a_thresh_tl, std::vector<long_t> configbit);

  // transformation biological weight <-> discrete weight (represented in index of look-up table)
  uint_t weight_to_entry_(double_t weight, double_t weight_per_lut_entry);
  double_t entry_to_weight_(uint_t discrete_weight, double_t weight_per_lut_entry);

  uint_t lookup_(uint_t discrete_weight_, std::vector<long_t> table);

  // data members of each connection
  double_t a_causal_;
  double_t a_acausal_;
  double_t a_thresh_th_;
  double_t a_thresh_tl_;

  bool init_flag_;
  long_t synapse_id_;
  double_t next_readout_time_;
  uint_t discrete_weight_; //TODO: TP: only needed in send, move to common properties or "static"?
  };

inline
bool STDPFACETSHWConnectionHom::eval_function_(double_t a_causal, double_t a_acausal, double_t a_thresh_th, double_t a_thresh_tl, std::vector<long_t> configbit)
{
  // compare charge on capacitors with thresholds and return evaluation bit
  return (a_thresh_tl + configbit[2] * a_causal + configbit[1] * a_acausal)
          / (1 + configbit[2] + configbit[1])
          > (a_thresh_th + configbit[0] * a_causal + configbit[3] * a_acausal)
          / (1 + configbit[0] + configbit[3]);
}

inline
uint_t STDPFACETSHWConnectionHom::weight_to_entry_(double_t weight, double_t weight_per_lut_entry)
{
  // returns the discrete weight in terms of the look-up table index
  return round(weight / weight_per_lut_entry);
}

inline
double_t STDPFACETSHWConnectionHom::entry_to_weight_(uint_t discrete_weight, double_t weight_per_lut_entry)
{
  // returns the continuous weight
  return discrete_weight * weight_per_lut_entry;
}

inline
uint_t STDPFACETSHWConnectionHom::lookup_(uint_t discrete_weight_, std::vector<long_t> table)
{
  // look-up in table
  return table[discrete_weight_];
}

inline
  void STDPFACETSHWConnectionHom::check_connection(Node & s, Node & r, rport receptor_type, double_t t_lastspike)
{
  ConnectionHetWD::check_connection(s, r, receptor_type, t_lastspike);
  r.register_stdp_connection(t_lastspike - Time(Time::step(delay_)).get_ms());
}

/**
 * Send an event to the receiver of this connection.
 * \param e The event to send
 * \param p The port under which this connection is stored in the Connector.
 * \param t_lastspike Time point of last spike emitted
 */
inline
void STDPFACETSHWConnectionHom::send(Event& e, double_t t_lastspike, STDPFACETSHWHomCommonProperties &cp)
{
  // synapse STDP dynamics

  double_t t_spike = e.get_stamp().get_ms();

  //init the readout time
  if(init_flag_ == false){
    synapse_id_ = cp.no_synapses_;
    ++cp.no_synapses_;
    cp.calc_readout_cycle_duration_();
    next_readout_time_ = int(synapse_id_ / cp.synapses_per_driver_) * cp.driver_readout_time_;
    std::cout << "init synapse " << synapse_id_ << " - first readout time: " << next_readout_time_ << std::endl;
    init_flag_ = true;
  }

  //STDP controller is processing this synapse (synapse driver)?
  if(t_spike > next_readout_time_)
  {
    //transform weight to discrete representation
    discrete_weight_ = weight_to_entry_(weight_, cp.weight_per_lut_entry_);

    //obtain evaluation bits
    bool eval_0 = eval_function_(a_causal_, a_acausal_, a_thresh_th_, a_thresh_tl_, cp.configbit_0_);
    bool eval_1 = eval_function_(a_causal_, a_acausal_, a_thresh_th_, a_thresh_tl_, cp.configbit_1_);

    //select LUT, update weight and reset capacitors
    if(eval_0 == true && eval_1 == false){
      discrete_weight_ = lookup_(discrete_weight_, cp.lookuptable_0_);
      if(cp.reset_pattern_[0]) a_causal_ = 0;
      if(cp.reset_pattern_[1]) a_acausal_ = 0;
    } else if(eval_0 == false && eval_1 == true){
      discrete_weight_ = lookup_(discrete_weight_, cp.lookuptable_1_);
      if(cp.reset_pattern_[2]) a_causal_ = 0;
      if(cp.reset_pattern_[3]) a_acausal_ = 0;
    } else if(eval_0 == true && eval_1 == true){
      discrete_weight_ = lookup_(discrete_weight_, cp.lookuptable_2_);
      if(cp.reset_pattern_[4]) a_causal_ = 0;
      if(cp.reset_pattern_[5]) a_acausal_ = 0;
    }
    //do nothing, if eval_0 == false and eval_1 == false

    while(t_spike > next_readout_time_){
      next_readout_time_ += cp.readout_cycle_duration_;
    }
    //std::cout << "synapse " << synapse_id_ << " updated at " << t_spike << ", next readout time: " << next_readout_time_ << std::endl;

    //back-transformation to continuous weight space
    weight_ = entry_to_weight_(discrete_weight_, cp.weight_per_lut_entry_);
  }

  // t_lastspike_ = 0 initially

  double_t dendritic_delay = Time(Time::step(delay_)).get_ms();

  //get spike history in relevant range (t1, t2] from post-synaptic neuron
  std::deque<histentry>::iterator start;
  std::deque<histentry>::iterator finish;
  target_->get_history(t_lastspike - dendritic_delay, t_spike - dendritic_delay,
			       &start, &finish);
  //facilitation due to post-synaptic spikes since last pre-synaptic spike
  double_t minus_dt = 0;
  double_t plus_dt = 0;

  if(start != finish) //take only first postspike after last prespike
  {
    minus_dt = t_lastspike - (start->t_ + dendritic_delay);
  }

  if(start != finish) //take only last postspike before current spike
  {
    --finish;
    plus_dt = (finish->t_ + dendritic_delay) - t_spike;
  }

  if(minus_dt != 0){
    a_causal_ += std::exp(minus_dt / cp.tau_plus_);
  }

  if(plus_dt != 0){
    a_acausal_ += std::exp(plus_dt / cp.tau_minus_);
  }

  e.set_receiver(*target_);
  e.set_weight(weight_);
  e.set_delay(delay_);
  e.set_rport(rport_);
  e();

  }
} // of namespace nest

#endif // of #ifndef STDP_CONNECTION_HOM_H
