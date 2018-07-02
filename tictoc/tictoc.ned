simple Txc 
{
    parameters:
        @display("i=block/routing");  // add a default icon
    gates:
        input in[];
        output out[];
}


network Tictoc 
{
    submodules:
        tic[6]: Txc;
    connections:
        tic[0].out++ --> { delay = 100ms; } --> tic[1].in++;
        tic[0].in++ <-- { delay = 100ms; } <-- tic[1].out++;

        tic[1].out++ --> { delay = 100ms; } --> tic[2].in++;
        tic[1].in++ <-- { delay = 100ms; } <-- tic[2].out++;

        tic[1].out++ --> { delay = 100ms; } --> tic[4].in++;
        tic[1].in++ <-- { delay = 100ms; } <-- tic[4].out++;

        tic[3].out++ --> { delay = 100ms; } --> tic[4].in++;
        tic[3].in++ <-- { delay = 100ms; } <-- tic[4].out++;

        tic[4].out++ --> { delay = 100ms; } --> tic[5].in++;
        tic[4].in++ <-- { delay = 100ms; } <-- tic[5].out++;
}
