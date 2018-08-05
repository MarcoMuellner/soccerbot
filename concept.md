# Software concept soccerbot

## Proposed features
* Creation of channels (each channel representing a specific matchday for a 
given league)
* Automated posting of match highlights within said channels
* Announcements of matchday starts
* Automated deletion of channels within a configurable timer
* Storing of all content within a given channel

## Basic software structure

* _Timerstructure_: Expose certain functions at given points in time
* _Channelcreation_: Variable creation of channels, with given name and 
association of a given ID
* _Sniffer_: Reading of all content within a given channel. This includes name, 
time, content. Should be opt-out for users
* ...

## So what is needed?
* _Language_: In principle there are multiple languages in which this bot 
can be written. Python would probably be the easiest, Node the most
feature complete.
* _Architecture_: The architecture is to be determined, depending on the
choice of language. If we use Node, we need to write a fully functional 
thing.

Api: https://api.qa.fifa.com/Help