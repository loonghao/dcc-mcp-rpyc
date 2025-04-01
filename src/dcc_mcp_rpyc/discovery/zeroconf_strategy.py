"""ZeroConf-based service discovery strategy for DCC-MCP-RPYC.

This module provides a service discovery strategy that uses ZeroConf (mDNS/DNS-SD) to register and discover services.
"""

# Import built-in modules
import logging
import socket
import time
from typing import List
from typing import Optional

try:
    # Import third-party modules
    from zeroconf import ServiceBrowser
    from zeroconf import ServiceInfo
    from zeroconf import Zeroconf
    from zeroconf.const import _TYPE_A

    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False


# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceDiscoveryStrategy
from dcc_mcp_rpyc.discovery.base import ServiceInfo as DccServiceInfo

# Configure logging
logger = logging.getLogger(__name__)

# Define service type for DCC MCP services
DCC_MCP_SERVICE_TYPE = "_dcc-mcp._tcp.local."


def get_local_ip() -> str:
    """Get the local IP address of the machine.

    Returns:
        Local IP address as a string

    """
    try:
        # Create a socket and connect to an external server
        # This doesn't actually establish a connection, but gives us the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google's DNS server
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.warning(f"Error getting local IP: {e}")
        return "127.0.0.1"  # Fallback to localhost


class ServiceListener:
    """Listener for ZeroConf service discovery.

    This class handles service discovery events from ZeroConf.
    """

    def __init__(self, dcc_name: Optional[str] = None):
        """Initialize the service listener.

        Args:
            dcc_name: Name of the DCC to filter services by (default: None, all DCCs)

        """
        self.dcc_name = dcc_name.lower() if dcc_name else None
        self.services = {}

    def add_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        """Handle service added event.

        Args:
            zeroconf: ZeroConf instance
            type_: Service type
            name: Service name

        """
        info = zeroconf.get_service_info(type_, name)
        if not info:
            return

        try:
            # Extract service properties
            properties = {}
            for key, value in info.properties.items():
                try:
                    key_str = key.decode("utf-8")
                    value_str = value.decode("utf-8")
                    properties[key_str] = value_str
                except UnicodeDecodeError:
                    # Skip binary properties
                    pass

            # Extract DCC name from properties
            dcc_name = properties.get("dcc_name", "").lower()

            # Filter by DCC name if specified
            if self.dcc_name and dcc_name != self.dcc_name:
                return

            # Create service entry
            addresses = []
            for address_type, addresses_list in info.addresses_by_version.items():
                if address_type == _TYPE_A:  # IPv4
                    for addr in addresses_list:
                        ip = socket.inet_ntoa(addr)
                        addresses.append(ip)

            if not addresses:
                return

            service_name = properties.get("service_name", name.split(".")[0])

            self.services[name] = {
                "name": service_name,
                "host": addresses[0],  # Use first IPv4 address
                "port": info.port,
                "dcc_name": dcc_name,
                "properties": properties,
                "timestamp": time.time(),
            }

            logger.debug(f"Added service: {service_name} ({dcc_name}) at {addresses[0]}:{info.port}")
        except Exception as e:
            logger.error(f"Error adding service {name}: {e}")

    def remove_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        """Handle service removed event.

        Args:
            zeroconf: ZeroConf instance
            type_: Service type
            name: Service name

        """
        if name in self.services:
            service = self.services[name]
            logger.debug(f"Removed service: {service['name']} ({service['dcc_name']})")
            del self.services[name]

    def update_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        """Handle service updated event.

        Args:
            zeroconf: ZeroConf instance
            type_: Service type
            name: Service name

        """
        self.add_service(zeroconf, type_, name)


class ZeroConfDiscoveryStrategy(ServiceDiscoveryStrategy):
    """ZeroConf-based service discovery strategy.

    This strategy uses ZeroConf (mDNS/DNS-SD) to register and discover services.
    """

    def __init__(self):
        """Initialize the ZeroConf discovery strategy."""
        self._zeroconf = None
        self._services = {}

        if not ZEROCONF_AVAILABLE:
            logger.warning("ZeroConf is not available. Please install the zeroconf package.")

    def _ensure_zeroconf(self) -> bool:
        """Ensure ZeroConf is available and initialized.

        Returns:
            True if ZeroConf is available, False otherwise

        """
        if not ZEROCONF_AVAILABLE:
            return False

        if self._zeroconf is None:
            try:
                self._zeroconf = Zeroconf()
            except Exception as e:
                logger.error(f"Error initializing ZeroConf: {e}")
                return False

        return True

    def discover_services(self, dcc_type: Optional[str] = None) -> List[DccServiceInfo]:
        """Discover available services.

        Args:
            dcc_type: Optional type of service to discover (e.g., 'maya', 'houdini')

        Returns:
            List of discovered ServiceInfo objects

        """
        if not self._ensure_zeroconf():
            return []

        # Create service listener
        listener = ServiceListener(dcc_type)

        # Browse for services
        ServiceBrowser(self._zeroconf, DCC_MCP_SERVICE_TYPE, listener)

        # Wait for services to be discovered (2 seconds)
        time.sleep(2.0)

        # Convert discovered services to ServiceInfo objects
        services = []
        for name, service_data in listener.services.items():
            try:
                service_info = DccServiceInfo(
                    name=service_data["name"],
                    host=service_data["host"],
                    port=service_data["port"],
                    dcc_type=service_data["dcc_name"],
                    metadata=service_data["properties"],
                )
                services.append(service_info)
            except Exception as e:
                logger.warning(f"Error creating ServiceInfo for {name}: {e}")

        # Update internal services cache
        for service in services:
            key = f"{service.dcc_type}:{service.name}:{service.host}:{service.port}"
            self._services[key] = service

        return services

    def register_service(self, service_info: DccServiceInfo) -> bool:
        """Register a service with the discovery mechanism.

        Args:
            service_info: Information about the service to register

        Returns:
            True if registration was successful, False otherwise

        """
        if not self._ensure_zeroconf():
            return False

        try:
            # Create service properties
            properties = {"dcc_name": service_info.dcc_type, "service_name": service_info.name}

            # Add metadata to properties
            for key, value in service_info.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    properties[key] = str(value)

            # Create service name
            service_name = f"{service_info.name}.{DCC_MCP_SERVICE_TYPE}"

            # Convert hostname to IP address
            host = service_info.host
            try:
                # Try to resolve the hostname to an IP address
                if host == "localhost" or host.startswith("localhost."):
                    host = "127.0.0.1"
                # Validate the IP address
                socket.inet_aton(host)
            except OSError:
                # If not a valid IP address, try to resolve the hostname
                try:
                    host = socket.gethostbyname(host)
                except socket.gaierror:
                    logger.warning(f"Cannot resolve hostname {host}, using default IP 127.0.0.1")
                    host = "127.0.0.1"

            # Create service info
            info = ServiceInfo(
                type_=DCC_MCP_SERVICE_TYPE,
                name=service_name,
                addresses=[socket.inet_aton(host)],
                port=service_info.port,
                properties={k.encode("utf-8"): v.encode("utf-8") for k, v in properties.items()},
            )

            # Register service
            self._zeroconf.register_service(info)

            # Update internal services cache
            key = f"{service_info.dcc_type}:{service_info.name}:{service_info.host}:{service_info.port}"
            self._services[key] = service_info

            logger.info(f"Service {service_info.name} registered, DCC type {service_info.dcc_type}")
            return True
        except Exception as e:
            logger.error(f"Service registration failed: {e}")
            return False

    def unregister_service(self, service_info: DccServiceInfo) -> bool:
        """Unregister a service from the discovery mechanism.

        Args:
            service_info: Information about the service to unregister

        Returns:
            True if unregistration was successful, False otherwise

        """
        if not self._ensure_zeroconf():
            return False

        try:
            # Create service name
            service_name = f"{service_info.name}.{DCC_MCP_SERVICE_TYPE}"

            # Convert hostname to IP address
            host = service_info.host
            try:
                # Try to resolve the hostname to an IP address
                if host == "localhost" or host.startswith("localhost."):
                    host = "127.0.0.1"
                # Validate the IP address
                socket.inet_aton(host)
            except OSError:
                # If not a valid IP address, try to resolve the hostname
                try:
                    host = socket.gethostbyname(host)
                except socket.gaierror:
                    logger.warning(f"Cannot resolve hostname {host}, using default IP 127.0.0.1")
                    host = "127.0.0.1"

            # Create service info
            info = ServiceInfo(
                type_=DCC_MCP_SERVICE_TYPE,
                name=service_name,
                addresses=[socket.inet_aton(host)],
                port=service_info.port,
                properties={},
            )

            # Unregister service
            self._zeroconf.unregister_service(info)

            # Update internal services cache
            key = f"{service_info.dcc_type}:{service_info.name}:{service_info.host}:{service_info.port}"
            if key in self._services:
                del self._services[key]

            logger.info(f"Service {service_info.name} unregistered, DCC type {service_info.dcc_type}")
            return True
        except Exception as e:
            logger.error(f"Service unregistration failed: {e}")
            return False

    def unregister_service_by_name(self, service_name: str) -> bool:
        """Unregister a service from the discovery mechanism by name.

        Args:
            service_name: Name of the service to unregister

        Returns:
            True if unregistration was successful, False otherwise

        """
        if not self._ensure_zeroconf():
            return False

        try:
            # Create full service name
            full_service_name = f"{service_name}.{DCC_MCP_SERVICE_TYPE}"

            # Find service in internal cache
            service_to_remove = None
            for key, service in self._services.items():
                if service.name == service_name:
                    service_to_remove = service
                    break

            if service_to_remove:
                return self.unregister_service(service_to_remove)

            # If service not found in cache, create a temporary service info object
            # This is not an ideal method, but allows unregistering services registered by other processes
            info = ServiceInfo(
                type_=DCC_MCP_SERVICE_TYPE,
                name=full_service_name,
                addresses=[socket.inet_aton("127.0.0.1")],  # Temporary address
                port=0,  # Temporary port
                properties={},
            )

            # Unregister service
            self._zeroconf.unregister_service(info)

            logger.info(f"Service {service_name} unregistered")
            return True
        except Exception as e:
            logger.error(f"Service unregistration by name failed: {e}")
            return False

    def __del__(self):
        """Clean up ZeroConf resources when the strategy is destroyed."""
        if self._zeroconf:
            try:
                self._zeroconf.close()
            except Exception as e:
                logger.error(f"Error closing ZeroConf: {e}")
