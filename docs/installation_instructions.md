# Installation Instructions for Production in EC2 Instance (prior to 3/2022) 

These are the installation instructions for the Meals on Wheels management system developed by the UVA Capstone Meals on Wheels team. These instructions have three parts:

1. Provision an AWS instance
2. Install Docker, Docker Compose, and Make
3. Install the application

## Provision an AWS instance
First, register or login to an account on AWS and log in to the EC2 console in order to provision an instance. We recommend using "Ubuntu Server 18.04 LTS (HVM), SSD Volume Type" as the AMI. Next we recommend using at least a T2-small instance with protection for accidental termination (termination protection located on next page). We also recommend for storage a General Prupose SSD of 20 GB. There are no tags that need to be added, but in the configure security group page, add the default rules for HTTP and HTTPS from the Add Rule button in addition for the default rule for SSH. (If testing in a non-production environment, also allow port 8000). When prompted, create a new key pair and save the key somewhere safe and accessible. 

## Install Docker, Docker Compose, and Make

First, connect to your instance by right clicking on it in the dashboard and selecting Connect. Once connected, run the following commands

```
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo curl -L https://github.com/docker/compose/releases/download/1.25.4/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo apt update
sudo apt install make
sudo reboot
```

Now we let the app reboot before right clicking and connecting again. 

## Install the Application

To download the code and run the application run the following commands. 

```
curl -fsSL http://cs.virginia.edu/~awh4kc/githubkey.gpg -o ~/.ssh/githubkey.gpg
cd ~/.ssh
gpg githubkey.gpg
```

Use password: `M#gh7fRH06nD`

```
eval "$(ssh-agent -s)"
chmod 600 ~/.ssh/githubkey
ssh-add ~/.ssh/githubkey
cd ~
git clone git@github.com:uva-cp-1920/Meals-on-Wheels.git
```

type `yes` when prompted

```
cd ~/Meals-on-Wheels/src
make env=prod deploy

```

Now you can verify the app is running by going to portal.cvillemeals.org in a browser. 
