#include <string.h>
#include <omnetpp.h>

using namespace omnetpp;

/**
 * Derive the Txc class from cSimpleModule. In the Tictoc1 network,
 * both the `tic' and `toc' modules are Txc objects, created by OMNeT++
 * at the beginning of the simulation.
 */
class Txc : public cSimpleModule
{
protected:
    // The following redefined virtual function holds the algorithm.
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
private:
    int counter;  // Note the counter here
};

// The module class needs to be registered with OMNeT++
Define_Module(Txc);

void Txc::initialize()
{
    // Initialize is called at the beginning of the simulation.
    // To bootstrap the tic-toc-tic-toc process, one of the modules needs
    // to send the first message. Let this be `tic'.

    // Am I Tic or Toc?
    if (par("sendMsgOnInit").boolValue() == true) {
        // Create and send the first message on gate "out". "tictocMsg" is an
        // arbitrary string which will be the name of the message object.
        cMessage *msg = new cMessage("tictocMsg");
        EV << "Sending initial message\n";
        send(msg, "out");
    }

    // Initialize counter. We'll decrement it every time and delete
    // the message when it reaches zero.
    counter = par("limit");

    // The WATCH() statement below will let you examine the variable in GUI.
    WATCH(counter);
}

void Txc::handleMessage(cMessage *msg)
{
    counter--;
    if (counter == 0) {
        // If counter is zero, delete message. If you run the model, you'll
        // find that the simulation will stop at this point with the message
        // "no more events"
        EV << getName() << "'s counter reached zero, deleting message\n";
        delete msg;
    } else {
        // Here, we just send it to the other module, through
        // gate `out'. Because both `tic' and `toc' does the same, the message
        // will bounce between the two.
        EV << getName() << "'s counter is " << counter << ", sending back message\n";
        send(msg, "out");  // send out the message
    }
}
