# Linux Setup

Accessing label and receipt printers using WebUSB on Linux requires configuring
udev so that the device nodes are accessible by the user running the browser and
the usblp driver must be detached. udev rules and scripts are included with this
project and can be installed by running the following command:

```sh
curl https://raw.githubusercontent.com/anthroarts/artshow-jockey/main/udev/install.sh | sudo sh
```
