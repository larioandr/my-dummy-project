simple Txc 
{
    parameters:
        bool sendMsgOnInit = default(false);  // whether the module should send 
                                              // out a message on initialization
        int limit = default(2);  // another parameter with a default value
        @display("i=block/routing");  // add a default icon
    gates:
        input in;
        output out;
}

simple Tic extends Txc 
{
    parameters:
        @display("i=,cyan");
        sendMsgOnInit = true;
}

simple Toc extends Txc
{
    parameters:
        @display("i=,gold");
        sendMsgOnInit = false;
}

//
// Two instances (tic and toc) of Txc1 connected both ways.
// Tic and toc will pass messages to one another.
//
network Tictoc 
{
    submodules:
        tic: Tic;
        toc: Toc;
    connections:
        tic.out --> { delay = 100ms; } --> toc.in;
        tic.in <-- { delay = 100ms; } <-- toc.out;
}
