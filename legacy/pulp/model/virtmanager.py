from property import Property
import logging


class VirtManager(object):
    
    def list_all_distros(self):
        print "list all distros!"
        data = []
        distro1 = Property()
        distro1.id = str('1')
        distro1.name ="RHEL5.1"
        distro1.type ="redhat"
        distro1.arch ="i386"
        
        distro2 = Property()
        distro1.id = str('2')
        distro2.name ="RHEL5.2"
        distro2.type ="redhat"
        distro2.arch ="i386"

        distro3 = Property()
        distro1.id = str('4')
        distro3.name ="RHEL4.6"
        distro3.type ="redhat"
        distro3.arch ="x86_64"
        
        data.append(distro1)
        data.append(distro2)
        data.append(distro3)
        return data 
