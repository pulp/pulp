# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
 config.vm.box = "humaton/fedora-21-cloud"
 config.vm.host_name = "pulp-devel"
 # config.vm.synced_folder "..", "/home/vagrant/devel", type: :rsync
 config.vm.synced_folder "..", "/home/vagrant/devel", type: "rsync"
 config.vm.synced_folder ".", "/home/vagrant/devel/pulp", type: "rsync"

 config.vm.provider :libvirt do |domain|
   domain.memory = 2048
   domain.cpus   = 2
 end

 config.vm.provision "shell", inline: "yum install -y deltarpm"
 config.vm.provision "shell", inline: "yum update -y"
 config.vm.provision "shell", inline: "yum install -y vagrant vagrant-libvirt vagrant-lxc"
 config.vm.provision "shell", inline: "sudo -u vagrant bash -e /home/vagrant/devel/pulp/playpen/vagrant-setup.sh"
end
