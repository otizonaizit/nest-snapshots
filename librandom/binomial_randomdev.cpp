/*
 *  binomial_randomdev.cpp
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


/* ---------------------------------------------------------------- 
 * Draw a binomial random number using the BP algoritm
 * Sampling From the Binomial Distribution on a Computer
 * Author(s): George S. Fishman
 * Source: Journal of the American Statistical Association, Vol. 74, No. 366 (Jun., 1979), pp. 418-423
 * Published by: American Statistical Association
 * Stable URL: http://www.jstor.org/stable/2286346 .
 * ---------------------------------------------------------------- */


#include "binomial_randomdev.h"
#include "dictutils.h"
#include <cmath>

librandom::BinomialRandomDev::BinomialRandomDev(RngPtr r_s, 
						double p_s, 
						unsigned int n_s)
 : RandomDev(r_s), poisson_dev_(r_s), exp_dev_(r_s), p_(p_s), n_(n_s)
{
  check_params_();
  PrecomputeTable(n_s);
}

librandom::BinomialRandomDev::BinomialRandomDev(double p_s,
						unsigned int n_s)
 : RandomDev(), poisson_dev_(), exp_dev_(), p_(p_s), n_(n_s)
{
  check_params_();
  PrecomputeTable(n_s);
}


void librandom::BinomialRandomDev::PrecomputeTable(size_t nmax)
{
    // precompute the table of f
    f_.resize( nmax+2 );
    f_[0] = 0.0;
    f_[1] = 0.0;    
    unsigned long i, j;
    i = 1;
    while (i < f_.size()-1){
        f_[i+1] = 0.0;
        j = 1;
        while (j<=i){
	  f_[i+1] += std::log(static_cast<double>(j));
            j++;
            }
        i++;
        }
    n_tablemax_ = nmax;
}


unsigned long librandom::BinomialRandomDev::uldev(RngPtr rng)
{
    assert(rng.valid());
    
    // BP algorithm (steps numbered as in Fishman 1979)
    unsigned long  X_;
    double q_, phi_, theta_, mu_, V_;
    long  Y_, m_;

    // 1, 2
    if (p_>0.5) 
        {
        q_ = 1.-p_;
        }
    else
        {
        q_ = p_;
        }
    
    // 3,4
    long n1mq = static_cast<long> ( static_cast<double>(n_) * (1.-q_)); 
    double n1mq_dbl = static_cast<double>(n1mq);
    if ( static_cast<double>(n_)*(1.-q_) - n1mq_dbl  > q_)
        {
        mu_ = q_* (n1mq_dbl + 1.) / (1.-q_);
        }
    else
        {
        mu_ = static_cast<double>(n_) - n1mq_dbl;
        }
    
    //5, 6, 7
    theta_ = (1./q_ - 1.) * mu_;
    phi_ = std::log(theta_);
    m_ = static_cast<long> (theta_);
    
    bool not_finished = 1;
    poisson_dev_.set_lambda( mu_ );
    while (not_finished)
        {
        //8,9
        X_ = n_+1;
        while( X_ > n_)
            {
            X_ = poisson_dev_.uldev(rng);
            }
        
        //10
        V_ = exp_dev_(rng);
        
        //11
        Y_ = n_ - X_;
        
        //12
        if ( V_ < static_cast<double>(m_-Y_)*phi_ - f_[m_+1] + f_[Y_+1] )
            {
            not_finished = 1;
            }
        else
            {
            not_finished = 0;
            }        
        }
    if (p_ <= 0.5)
        {
        return X_;
        }
    else
        {
        return static_cast<unsigned long>(Y_);
        }
}


void librandom::BinomialRandomDev::set_p_n(double p_s, unsigned int n_s)
{
  p_ = p_s;
  n_ = n_s;
  check_params_();
  if (n_s > n_tablemax_)
    {
    PrecomputeTable(n_s);
    }
}

void librandom::BinomialRandomDev::set_p(double p_s)
{
  p_ = p_s;
  check_params_();
}

void librandom::BinomialRandomDev::set_n(unsigned int n_s)
{
  n_ = n_s;
  check_params_();
  if (n_s > n_tablemax_)
    {
    PrecomputeTable(n_s);
    }
} 

void librandom::BinomialRandomDev::check_params_()
{
  assert( 0.0 <= p_ && p_ <= 1.0 );
}

void librandom::BinomialRandomDev::set_status(const DictionaryDatum &d)
{
  double p_tmp;
  if (  updateValue<double>(d, "p", p_tmp) )
    set_p(p_tmp);

  long n_tmp;
  if (  updateValue<long>(d, "n", n_tmp) )
    set_n(n_tmp);
} 

void librandom::BinomialRandomDev::get_status(DictionaryDatum &d) const 
{
  def<double>(d, "p", p_);
  def<long>(d, "n", n_);
}
