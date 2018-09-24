import sys
import os
import time

from novaclient import client as nova_client
from novaclient import exceptions as nova_exception

class OpenStackNovaHelper(object):
    
    FLAVORS = {'1cpu1024m': 'm2.tiny',
               '1cpu2048m': 'm2.small',
               '2cpu2048m': 'm2.medium',
               '2cpu4096m': 'm3.medium'}
    
    def __init__(self, api_version="2", log=None, username=None, password=None, tenant_name=None, auth_url=None):
        try:
            self.client = nova_client.Client(api_version, os.environ['OS_USERNAME'] if username is None else username,
                                                          os.environ['OS_PASSWORD'] if password is None else password,
                                                          os.environ['OS_TENANT_NAME'] if tenant_name is None else tenant_name,
                                                          os.environ['OS_AUTH_URL'] if auth_url is None else auth_url)
        except Exception, ex:
            print "Failed to create Nova client: %s" % str(ex)
            raise ex
        
        self.log = log
    
    def _log_error(self, err):
        self.error = err
        if self.log is not None:
            self.log.error(err)
        else:
            print err
    
    def get_error(self):
        return self.error
    
    def create_instance(self, name, image, flavor="m2.small", security_groups=['default'], networks=['defaultnetwork'], wait_status=None):
        try:
            assert self.get_instance(name=name) is None, "Instance '%s' already exists" % name
            assert self.get_image(name=image) is not None, self.get_error()
            assert self.get_flavor(name=flavor) is not None, self.get_error()
            for sec_group in security_groups:
                assert sec_group in self.list_security_groups(), "Security group '%s' not found" % sec_group
            for nw in networks:
                assert self.get_network(nw) is not None, self.get_error()
            
            nics = []
            for net in networks:
                network = self.get_network(net)
                if network is not None: 
                    nics.append({'net-id': network['id']})
            
            instance = self.client.servers.create(name=name,
                                                  image=self.get_image(image)['id'],
                                                  flavor=self.get_flavor(name=flavor)['id'],
                                                  security_groups=security_groups,
                                                  nics=nics)
            
            if wait_status:
                assert self.wait_instance_status(name, status=wait_status), self.get_error()
            
            return self.get_instance(instance_obj=instance, get_console=False)
        except Exception, ex:
            self._log_error("ERROR: Failed to create instance '%s': %s" % (name, str(ex)))
            return None
    
    def wait_instance_status(self, instance_name, status="ACTIVE", timeout_seconds=300):
        instance = self.get_instance(instance_name, get_console=False)
        if instance is None:
            return False
        
		start_time = time.time()
        while True:
            if instance is not None and 'status' in instance and instance['status'] == status:
                break
            if (time.time() - start_time) > timeout_seconds:
                self._log_error("Instance '%s' did not get status '%s' within %i seconds" % (instance_name, status, timeout_seconds))
                return False
            time.sleep(5)
            instance = self.get_instance(instance_name, get_console=False)
        
		# assigning networks to instance is delayed
        for i in range(20):
            if len(instance['networks']) > 0:
                return True
            time.sleep(1)
            instance = self.get_instance(instance_name, get_console=False)
        self._log_error("No networks found for instance '%s'" % instance_name)
        return False
    
    def get_image(self, name=None, id=None, image_obj=None):
        try:
            if image_obj is None:
                image_obj = self.client.images.find(name=name) if name is not None else self.client.images.find(id=id)
            return {'name': image_obj.name,
                    'id': image_obj.id,
                    'status': image_obj.status,
                    'created': image_obj.created,
                    'updated': image_obj.updated}
        except nova_exception.NotFound:
            self._log_error("ERROR: Image '%s' not found" % name)
            return None
        except nova_exception.ClientException, ex:
            self._log_error("ERROR: Nova client exception: %s" % str(ex))
            return None
        
    def get_flavor(self, name=None, id=None, flavor_obj=None):
        try:
            if flavor_obj is None:
                flavor_obj = self.client.flavors.find(name=name) if name is not None else self.client.flavors.find(id=id)
            return {'name': flavor_obj.name,
                    'id': flavor_obj.id,
                    'vcpus': flavor_obj.vcpus,
                    'ram': flavor_obj.ram,
                    'disk': flavor_obj.disk}
        except nova_exception.NotFound:
            self._log_error("ERROR: Flavor '%s' not found" % name)
            return None
        except nova_exception.ClientException, ex:
            self._log_error("ERROR: Nova client exception: %s" % str(ex))
            return None

    def get_instance(self, name=None, instance_obj=None, get_console=False):
        try:
            if instance_obj is None:
                instance_obj = self.client.servers.find(name=name)
            return {'name': instance_obj.name,
                    'id': instance_obj.id,
                    'status': instance_obj.status,
                    'created': instance_obj.created,
                    'updated': instance_obj.updated,
                    'image': self.get_image(id=instance_obj.image['id']),
                    'flavor': self.get_flavor(id=instance_obj.flavor['id']),
                    'networks': instance_obj.networks,
                    'security_groups': [sg.name for sg in instance_obj.list_security_group()],
                    'console': instance_obj.get_spice_console("spice-html5") if get_console else None}
        except nova_exception.NotFound:
            self._log_error("ERROR: Instance '%s' not found" % name)
            return None
        except nova_exception.ClientException, ex:
            self._log_error("ERROR: Nova client exception: %s" % str(ex))
            return None
        
    def get_network(self, label):
        try:
            network = self.client.networks.find(label=label)
            return {'label': network.label,
                    'id': network.id}
        except nova_exception.NotFound:
            self._log_error("ERROR: Network '%s' not found" % label)
            return None
        except nova_exception.ClientException, ex:
            self._log_error("ERROR: Nova client exception: %s" % str(ex))
            return None

    def get_floating_ip(self, ip=None, floating_ip_obj=None):
        try:
            if floating_ip_obj is None:
                floating_ip_obj = self.client.floating_ips.find(ip=ip)
            return {'ip': floating_ip_obj.ip,
                    'id': floating_ip_obj.id,
                    'pool': floating_ip_obj.pool}
        except nova_exception.NotFound:
            self._log_error("ERROR: Floating IP '%s' not found" % ip)
            return None
        except nova_exception.ClientException, ex:
            self._log_error("ERROR: Nova client exception: %s" % str(ex))
            return None

    def create_floating_ip(self, pool="Ext-Access"):
        try:
            floating_ip = self.client.floating_ips.create(pool)
            return {'id': floating_ip.id,
                    'ip': floating_ip.ip,
                    'pool': floating_ip.pool}
        except Exception, ex:
            self._log_error("ERROR: Failed to create floating IP in pool '%s': %s" % (pool, str(ex)))
            return None
        
    def delete_floating_ip(self, floating_ip):
        try:
            floating_ip = self.client.floating_ips.find(ip=floating_ip)
            floating_ip.delete()
            return True
        except:
            self._log_error("ERROR: Failed to delete floating IP '%s': %s" % (floating_ip, str(ex)))
            return False
    
    def list_images(self):
        images = []
        for image in self.client.images.list():
            images.append(self.get_image(image_obj=image))
        return images
        
    def list_flavors(self):
        flavors = []
        for flavor in self.client.flavors.list():
            flavors.append(self.get_flavor(flavor_obj=flavor))
        return flavors

    def list_security_groups(self):
        security_groups = []
        for security_group in self.client.security_groups.list():
            security_groups.append(security_group.name)
        return security_groups
    
    def list_instances(self):
        instances = []
        for instance in self.client.servers.list():
            instances.append(self.get_instance(instance_obj=instance, get_console=False))
        return instances
    
    def list_floating_ips(self):
        floating_ips = []
        for floating_ip in self.client.floating_ips.list():
            floating_ips.append(self.get_floating_ip(floating_ip_obj=floating_ip))
        return floating_ips
    
    def add_security_group_to_instance(self, instance_name, security_group):
        try:
            instance = self.client.servers.find(name=instance_name)
            instance.add_security_group(security_group)
            return True
        except Exception, ex:
            self._log_error("ERROR: Failed to add security group '%s' to instance %s: %s" % (security_group, instance_name, str(ex)))
            return False
    
    def add_floating_ip_to_instance(self, instance_name, floating_ip):
        try:
            instance = self.client.servers.find(name=instance_name)
            instance.add_floating_ip(floating_ip)
            return True
        except Exception, ex:
            self._log_error("ERROR: Failed to add floating IP address '%s' to instance '%s': %s" % (floating_ip, instance_name, str(ex)))
            return False
    
    def reboot_instance(self, instance_name, reboot_type="SOFT"):
        try:
            instance = self.client.servers.find(name=instance_name)
            instance.reboot(reboot_type)
            return True
        except Exception, ex:
            self._log_error("ERROR: Failed to %s-reboot instance '%s': %s" % (reboot_type, instance_name, str(ex)))
            return False
    
    def suspend_instance(self, instance_name):
        try:
            instance = self.client.servers.find(name=instance_name)
            instance.suspend()
            return True
        except Exception, ex:
            self._log_error("ERROR: Failed to suspend instance '%s': %s" % (instance_name, str(ex)))
            return False
    
    def delete_instance(self, instance_name):
        try:
            instance = self.client.servers.find(name=instance_name)
            instance.delete()
            return True
        except Exception, ex:
            self._log_error("ERROR: Failed to delete instance '%s': %s" % (instance_name, str(ex)))
            return False
