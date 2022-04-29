#This code was adapted from the Bluetooth Linux Study Guide
# Available at: https://www.bluetooth.com/blog/the-bluetooth-for-linux-developers-study-guide/

# Broadcasts connectable advertising packets
import bluetooth_gatt
import random
import bluetooth_constants
import bluetooth_exceptions
import dbus
import dbus.exceptions
import dbus.service
import dbus.mainloop.glib
import sys
from gi.repository import GLib
sys.path.insert(0, '.')

bus = None
adapter_path = None
adv_mgr_interface = None

class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/ldsg/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = [bluetooth_constants.DRONE_RID_SVC_UUID]
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = 'Drone RID'
        self.include_tx_power = False
        self.data = None
        self.discoverable = True
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                                    signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids,
                                                    signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data,
                                                        signature='sv')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.discoverable is not None and self.discoverable == True:
            properties['Discoverable'] = dbus.Boolean(self.discoverable)
        if self.include_tx_power:
            properties['Includes'] = dbus.Array(["tx-power"], signature='s')

        if self.data is not None:
            properties['Data'] = dbus.Dictionary(
                self.data, signature='yv')
        print(properties)
        return {bluetooth_constants.ADVERTISING_MANAGER_INTERFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(bluetooth_constants.DBUS_PROPERTIES,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != bluetooth_constants.ADVERTISEMENT_INTERFACE:
            raise bluetooth_exceptions.InvalidArgsException()
        return self.get_properties()[bluetooth_constants.ADVERTISING_MANAGER_INTERFACE]

    @dbus.service.method(bluetooth_constants.ADVERTISING_MANAGER_INTERFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        print('%s: Released' % self.path)

def register_ad_cb():
    print('Advertisement registered OK')

def register_ad_error_cb(error):
    print('Error: Failed to register advertisement: ' + str(error))
    mainloop.quit()

def start_advertising():
    global adv
    global adv_mgr_interface
    # we're only registering one advertisement object so index (arg2) is hard coded as 0
    print("Registering advertisement",adv.get_path())
    adv_mgr_interface.RegisterAdvertisement(adv.get_path(), {},
                                        reply_handler=register_ad_cb,
                                        error_handler=register_ad_error_cb)
                                        

class DroneRIDCharacteristic(bluetooth_gatt.Characteristic):
	name = "name"
	drone_uuid = 0
	#notifying = False
	
	def __init__(self, bus, index, service):
		bluetooth_gatt.Characteristic.__init__(self, bus, index, bluetooth_constants.DRONE_RID_CHR_UUID,['read','notify'],service)
		self.name = "Drone1"
		self.drone_uuid = "10318a23-75d6-4868-bbf9-cee1804ed43d"
		print("Initial name set to "+str(self.name))
		

class DroneRIDService(bluetooth_gatt.Service):
	
	def __init__(self, bus, path_base, index):
		print("Initialising DroneRIDService object")
		bluetooth_gatt.Service.__init__(self, bus, path_base, index, bluetooth_constants.DRONE_RID_SVC_UUID, True)
		print("Adding TemperatureCharacteristic to the service")
		self.add_characteristic(DroneRIDCharacteristic(bus, 0, self))
		
class Application(dbus.service.Object):
	def __init__(self, bus):
		self.path = '/'
		self.services = []
		dbus.service.Object.__init__(self, bus, self.path)
		print("Adding DroneRIDService to the Application")
		self.add_service(DroneRIDService(bus, '/org/bluez/ldsg', 0))
		
	def get_path(self):
		return dbus.ObjectPath(self.path)
	
	def add_service(self, service):
		self.services.append(service)
		
	
	@dbus.service.method(bluetooth_constants.DBUS_OM_IFACE,out_signature='a{oa{sa{sv}}}')
	def GetManagedObjects(self):
		response = {}
		print('GetManagedObjects')
		
		for service in self.services:
			print("GetManagedObjects: service="+service.get_path())
			response[service.get_path()] = service.get_properties()
			chrcs = service.get_characteristics()
			for chrc in chrcs:
				response[chrc.get_path()] = chrc.get_properties()
				descs = chrc.get_descriptors()
				for desc in descs:
					response[desc.get_path()] = desc.get_properties()
		return response
	

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
# we're assuming the adapter supports advertising
adapter_path = bluetooth_constants.BLUEZ_NAMESPACE + bluetooth_constants.ADAPTER_NAME
print(adapter_path)

adv_mgr_interface = dbus.Interface(bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME,adapter_path), bluetooth_constants.ADVERTISING_MANAGER_INTERFACE)
# we're only registering one advertisement object so index (arg2) is hard coded as 0
adv = Advertisement(bus, 0, 'peripheral')
start_advertising()

print("Advertising as "+adv.local_name)

def register_app_cb():
	print('GATT application registered')

def register_app_error_cb(error):
	print('Failed to register application: ' + str(error))
	mainloop.quit()
	

app = Application(bus)
print('Registering GATT application...')
service_manager = dbus.Interface(bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME,adapter_path),bluetooth_constants.GATT_MANAGER_INTERFACE)
service_manager.RegisterApplication(app.get_path(), {},reply_handler=register_app_cb,error_handler=register_app_error_cb)

mainloop = GLib.MainLoop()
mainloop.run()

