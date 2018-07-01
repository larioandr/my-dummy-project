simple Txc 
{
    parameters:
        @display("i=block/routing");  // add a default icon
    gates:
        input in;
        output out;
}

simple Tic extends Txc 
{
    parameters:
        @display("i=,cyan");
        @class(Tic);
        double timeout @unit(s) = default(3s);  // time to wait for a reply from Toc
        int limit = default(2);  // a number of messages sent
}

simple Toc extends Txc
{
    parameters:
        @display("i=,gold");
        @class(Toc);
        double loseProb = default(0.1);  // a probability to lose the message
        volatile double delayTime @unit(s);  // processing duration
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
