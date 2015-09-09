emanage x900
============

emanage is a tool for performing maintenance of 11-cartridge Epson Stylus Pro printers, such as the 4900.
It permits nozzles to be checked and cleaned over the network from any machine.
The intention is to reduce the incidence of severe clogging and print head failures during intermittent use; by scheduling automated checks the printer can be exercised regularly, and any resulting problems can be addressed remotely.

This is not guaranteed to work with your printer. This may damage your printer. This may erase all of your favourite memories. Use this tool at your own risk.

Checking Nozzles
----------------
You need to know the hostname or IP address of your printer. For example, if your printer is at 192.168.1.10, issue:
```
emanage --check 192.168.1.10
```

A nozzle check will be performed. If any nozzles are found to be clogged, a message will be printed and the code 100 returned. A successful check returns 0.

Cleaning Nozzles
----------------
If blocked nozzles are found, they can be cleaned using the script. For example, to clean the orange nozzles, issue:
```
emanage --clean OR 192.168.1.10
```
For a list of the available colours, issue `emanage --help`.
Nozzles are cleaned in groups. For example, cleaning orange (OR) will also clean green (GR).
The printer appears to recheck the nozzles after cleaning. The updated nozzle check response is reported.
