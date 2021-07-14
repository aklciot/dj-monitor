# User guide
## Navigation menu
Using the navigation menu it is possible to view **Nodes** (sensors), **Repeaters** and **Gateways**. **Dashboard status** is a link to the network status page on Thingsboard. **About** and **Contact** are also available.

## Login & Profile
At the top right of the page it is possible login/logout. By clicking on your name you will bring up your profile page where you can change your password, modify your contact details and see which nodes etc you have alerts for.

### Update your details
This screen allows you to change your details. The _Email address, Mobile phone number & PushBullet access token_ info if used to enable notifications if nodes/repeaters/gateways go up or down. 

Notifications are enabled by node/repeater/gateway, you have to go into the details of the relevant item and say which notifications you want to get.
* Email - to enable email notifications enter your email address.
* SMS - to enable SMS notifications a valid mobile (NZ) number is required.
* [PushBullet](https://www.pushbullet.com/) can be installed on Android & Windows, and has Chrome & Firefox extensions. You will need to create an account and the get an *access code*. On the PushBullet web site, go to `Settings`, `Access tokens`, `Create Access Token`. Take the token displayed and save in your **Monitor profile**.

## Nodes / repeater / Gateway menus
These pages will display all the nodes, repeaters & gateways currently operating. 

#### Node menu
The nodes are separated by the projects they aare asssociated with, and nodes unallocated are shown at the bottom. Some data is shown on the node icon, the system attempts to get this data from the message queue, but it is also usful to add it yourself.

The colour of the node depicts their status
  - Green: Battery OK or no battery info available
  - Orange: Warning battery level
  - Red: Critical battery level
  - Black: Node down, the time from the last message to when it is marked down can be configured in the **Update details** section
