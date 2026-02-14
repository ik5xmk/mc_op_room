# mc_op_room
A suite of programs for LoRa MeshCom for small operations room management
<br><br>
- Logger: Read and transmit interface with the Lora card, with data saved to a database. Designed for future expansion to receive commands from applications.<br>
- Messages: Displays received messages in a window, with the option to filter incoming messages. You can send a reply by selecting the received group, and send it to the logger for transmission to the meshcom network.<br>
- Nodes: displays the coordinates of reachable nodes and calculates the distances from each node simply by selecting it as the origin.<br>
- Map: the only program in the suite that requires an internet connection to view nodes on a map, with the last listening time.<br><br>

Run the logger as the first software, and leave it listening for message packets and positions. Then run the others as soon as the first data arrives.<br><br>
You can find a complete explanation of how to use the software in this article (Google can help with translation), as well as programs developed for Windows:
<br>
[https://www.grupporadiofirenze.net/2026/01/16/un-software-per-gestire-off-grid-la-rete-lora-meshcom/](https://www.grupporadiofirenze.net/2026/01/16/un-software-per-gestire-off-grid-la-rete-lora-meshcom/)<br><br>
For information on the MeshCom project see here:
[MESHCOM](https://icssw.org/en/meshcom/)<br><br>
For details on the initial configuration of the lora cards and general information and useful links:
[https://www.grupporadiofirenze.net/2025/11/27/meshcom-una-rete-radioamatoriale-su-tecnologia-lora/](https://www.grupporadiofirenze.net/2025/11/27/meshcom-una-rete-radioamatoriale-su-tecnologia-lora/)<br><br>
These programs are written in Python, requiring libraries to be loaded manually, and you must be familiar with the environment and networking features, as well as knowing how to manage configurations on the Lora cards.<br>
So, use "pip install pyserial" and "pip install tkintermapviews" for example.<br>
Remember: run mc_logger from sudo/root to access the serial port and run mc_messages as user and not as root, and also other programs with a graphical interface.<br>
No liability or support is assumed for the use of the programs, which are intended for hobbyist and amateur radio use. They can be freely modified.<br><br>
![](https://github.com/ik5xmk/mc_op_room/blob/main/meshcom_op_room.jpg)<br>
