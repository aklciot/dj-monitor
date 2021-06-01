# Change log
This log records changes and updates to the IoT monitoring system
### 1 June 2021
* Added ability to modify notifications for other people, for users who are classified as 'staff'.

### 28 May 2021
* Changed notification icons to outlines

### 27 May 2021
* Remove HTML from message body when storing & displaying email notifications
* Add notification type icons on Node, repeater & Gateway menus

### 25 May 2021
* Created a log in the database for notifications sent out by this system.
* Notifications sent out are displayed on the node/repeater/gateway pages
* Improvements to the node data automatically collected

### 21 May 2021
* Added an about page with basic data of the innovation systems and links to more information
* Added a contacts page with email links
* Fixed issue with data going to a topic outside of AKLC/# with CSV data

### 18 May 2021
* Modified display of **node** page:
  - Black - node down
  - Red - Critical battery level for node
  - Orange - Warning battery level for node
  - Green - battery OK, or no battery info available
* Modified display of **repeater** page:
  - Black - repeater down
  - Blue - repeater up for under a week
  - Green - repeater up for more than a week
* Modified display of **gateway** page:
  - Black - gateway down
  - Blue - gateway up for under a day
  - Green - gateway up for more than a day

### 11 May 2021
* Added a profile page for users which enables them to:
  - Modify their personal detals, phone, email etc.
  - Change their password
  - View which nodes / repeaters / gateways they have set up notifications for

### 1 May 2021
* Added an MQTT log feature for all nodes. To access it, on the page for the node in question, click on the queue name of interest. It will display the last 50 messages received and auto updates every 60 sec. All MQTT messages for all queues are recorded and stored for 30 days.
