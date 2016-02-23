# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .__about__ import ( # noqa
    __author__, __copyright__, __email__, __license__, __summary__, __title__,
    __uri__, __version__,
)

_about_exports = [
    "__author__", "__copyright__", "__email__", "__license__", "__summary__",
    "__title__", "__uri__", "__version__",
]

from .acibaseobject import Tag # noqa
from .acicounters import ( # noqa
    AtomicCounter, AtomicCountersOnGoing, AtomicNode, AtomicPath,
    InterfaceStats,
)
from .aciHealthScore import HealthScore # noqa
from .aciSearch import AciSearch, Searchable # noqa
from .acisession import EventHandler, Login, Session, Subscriber # noqa
from .aciTable import Table # noqa
from .acitoolkit import ( # noqa
    AppProfile, BGPSession, BridgeDomain, CollectionPolicy, CommonEPG, Context,
    Contract, ContractInterface, Endpoint, EPG, EPGDomain, FexInterface,
    Filter, FilterEntry, L2ExtDomain, L2Interface, L3ExtDomain, L3Interface,
    LogicalModel, MonitorPolicy, MonitorStats, MonitorTarget, NetworkPool,
    OSPFInterface, OSPFInterfacePolicy, OSPFRouter, OutsideEPG, OutsideL3, OutsideNetwork,
    PhysDomain, PortChannel, Search, Subnet, Taboo, Tenant, TunnelInterface,
    VMM, VMMCredentials, VmmDomain, VMMvSwitchInfo,
)
from .acitoolkitlib import Credentials # noqa
# Dependent on acitoolkit
from .aciConcreteLib import ( # noqa
    ConcreteAccCtrlRule, ConcreteArp, ConcreteBD, ConcreteContext, ConcreteEp,
    ConcreteFilter, ConcreteFilterEntry, ConcreteLoopback, ConcreteOverlay,
    ConcretePortChannel, ConcreteSVI, ConcreteVpc, ConcreteVpcIf, ConcreteTunnel,
)
# Dependent on aciconcretelib
from .aciphysobject import ( # noqa
    Cluster, ExternalSwitch, Fabric, Fan, Fantray, Interface, Linecard, Link,
    Node, PhysicalModel, Pod, Powersupply, Process, Supervisorcard,
    Systemcontroller, WorkingData,
)

import inspect as _inspect

__all__ = _about_exports + sorted(
    name for name, obj in locals().items()
    if not (name.startswith('_') or _inspect.ismodule(obj))
)
