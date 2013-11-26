#ifndef CONNECTION_CREATOR_H
#define CONNECTION_CREATOR_H

/*
 *  connection_creator.h
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

#include <vector>
#include "network.h"
#include "position.h"
#include "topologymodule.h"
#include "topology_names.h"
#include "vose.h"
#include "mask.h"
#include "parameter.h"
#include "selector.h"

namespace nest
{
  template<int D>
  class Layer;

  /**
   * This class is a representation of the dictionary of connection
   * properties given as an argument to the ConnectLayers function. The
   * connect method is responsible for generating the connection according
   * to the given parameters. This method is templated with the dimension
   * of the layers, and is called via the Layer connect call using a
   * visitor pattern. The connect method relays to another method (e.g.,
   * convergent_connect_) implementing the concrete connection
   * algorithm. It would be more elegant if this was a base class for
   * classes representing different connection algorithms with a virtual
   * connect method, but it is not possible to have a virtual template
   * method.
   *
   * This class distinguishes between target driven and convergent
   * connections, which are both called "convergent" in the Topology module
   * documentation, and between source driven and divergent
   * connections. The true convergent/divergent connections are those with
   * a fixed number of connections (fan in/out). The only difference
   * between source driven and target driven connections is which layer
   * coordinates the mask and parameters are defined in.
   */
  class ConnectionCreator {
  public:

    enum ConnectionType {Target_driven, Source_driven, Convergent, Divergent, Population};
    typedef std::map<Name,lockPTR<Parameter> > ParameterMap;

    /**
     * Construct a ConnectionCreator with the properties defined in the
     * given dictionary.
     * @param dict dictionary containing properties for the connections.
     */
    ConnectionCreator(DictionaryDatum dict);

    /**
     * Connect two layers.
     * @param source source layer.
     * @param target target layer.
     */
    template<int D>
    void connect(Layer<D>& source, Layer<D>& target);

  private:

    template<int D>
    void target_driven_connect_(Layer<D>& source, Layer<D>& target);

    template<int D>
    void source_driven_connect_(Layer<D>& source, Layer<D>& target);

    template<int D>
    void convergent_connect_(Layer<D>& source, Layer<D>& target);

    template<int D>
    void divergent_connect_(Layer<D>& source, Layer<D>& target);

    /**
     * Calculate parameter values for this position.
     */
    template<int D>
    void get_parameters_(const Position<D> & pos, librandom::RngPtr rng, DictionaryDatum d);

    ConnectionType type_;
    bool allow_autapses_;
    bool allow_multapses_;
    bool allow_oversized_;
    Selector source_filter_;
    Selector target_filter_;
    index number_of_connections_;
    lockPTR<AbstractMask> mask_;
    lockPTR<Parameter> kernel_;
    index synapse_model_;
    ParameterMap parameters_;

    Network& net_;
  };

} // namespace nest

#endif
