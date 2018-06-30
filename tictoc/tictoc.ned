simple Txc {
    parameters:
        bool sendMsgOnInit = default(false);  // whether the module should send out a message on initialization
        int limit = default(2);  // another parameter with a default value
        @display("i=block/routing");  // add a default icon
    gates:
        input in;
        output out;
}


//
// Two instances (tic and toc) of Txc1 connected both ways.
// Tic and toc will pass messages to one another.
//
network Tictoc {
    submodules:
        tic: Txc {
            parameters:
                sendMsgOnInit = true;
                @display("i=,cyan");  // do not change the icon (first arg of i=) just colorize it
        }
        toc: Txc {
            parameters:
                sendMsgOnInit = false;
                @display("i=,gold");  // here too
        }
    connections:
        tic.out --> { delay = 100ms; } --> toc.in;
        tic.in <-- { delay = 100ms; } <-- toc.out;
}
