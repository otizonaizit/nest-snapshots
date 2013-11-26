/*
 *  gsl_binomial_randomdev.cpp
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

#include "gsl_binomial_randomdev.h"

#ifdef HAVE_GSL

#include "dictutils.h"

librandom::GSL_BinomialRandomDev::GSL_BinomialRandomDev(RngPtr r_s, double p_s, unsigned int n_s)
        : RandomDev(r_s), p_(p_s), n_(n_s)
{
  GslRandomGen* gsr_rng = dynamic_cast<GslRandomGen*>(&(*r_s));
  assert (gsr_rng && "r_s needs to be a GSL RNG");
  rng_ = gsr_rng->rng_;
}

librandom::GSL_BinomialRandomDev::GSL_BinomialRandomDev(double p_s, unsigned int n_s)
        : RandomDev(), p_(p_s), n_(n_s)
{}

unsigned long librandom::GSL_BinomialRandomDev::uldev()
{
  return gsl_ran_binomial(rng_, p_, n_);
}

unsigned long librandom::GSL_BinomialRandomDev::uldev(RngPtr rng) const
{
  GslRandomGen* gsr_rng = dynamic_cast<GslRandomGen*>(&(*rng));
  assert (gsr_rng && "rng needs to be a GSL RNG");
  return gsl_ran_binomial(gsr_rng->rng_, p_, n_);
}

void librandom::GSL_BinomialRandomDev::set_p(double p_s)
{
  assert( 0.0 <= p_ && p_ <= 1.0 );
  p_ = p_s;
}

void librandom::GSL_BinomialRandomDev::set_n(unsigned int n_s)
{
  n_ = n_s;
}

void librandom::GSL_BinomialRandomDev::set_status(const DictionaryDatum &d)
{
  double p_tmp;
  if (  updateValue<double>(d, "p", p_tmp) )
    set_p(p_tmp);

  long n_tmp;
  if (  updateValue<long>(d, "n", n_tmp) )
    set_n(n_tmp);
}

void librandom::GSL_BinomialRandomDev::get_status(DictionaryDatum &d) const
{
  def<double>(d, "p", p_);
  def<long>(d, "n", n_);
}

#endif
