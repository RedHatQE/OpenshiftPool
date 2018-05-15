# OpenshiftPool
an OpenShift On Openstack deployer

## Getting Started
1. Clone the project.
2. Create the ```config.yaml``` file from the [config template](https://github.com/gshefer/OpenshiftPool/blob/master/config/config.template.yaml).
3. Under the config directory, create another directory ```keys``` and under this directory create another directory called ```stack``` (so you'll have ```config/keys/stack``` directory). under this directory create the following files:
    * ```authorized_keys``` - This file should include all the authorized keys to provide SSH connection to the VMs.
    * ```id_rsa``` - The private key.
    * ```id_rsa.pub``` - The public key.
4. Create a virtual env. and activate it. (```python36 -m vent .env; . .env/bin/activate```)
5. Install requirements: ```pip install -Ur requirements.txt```
6. Now you can deploy cluster by using the cli.
    * Type ```python cli.py -h``` for help:
      ```bash
      usage: cli.py [-h] {create,deploy,delete} ...
      positional arguments:
        {create,deploy,delete}
                              operation
          create              Creating a cluster stack without deploy
          deploy              Deploying a cluster
          delete              Deleting a cluster
      optional arguments:
        -h, --help            show this help message and exit
      ```
