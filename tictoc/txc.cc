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
public:
    Txc();
    virtual ~Txc();
protected:
    // The following redefined virtual function holds the algorithm.
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
private:
    int counter;  // Note the counter here
    cMessage *event;  // pointer to the event object which we'll use for timing
    cMessage *tictocMsg;  // variable to remember the message until sent it
};

// The module class needs to be registered with OMNeT++
Define_Module(Txc);

Txc::Txc()
{
    // Set the pointer to nullptr, so that the destructor won't crash
    // even if initialize() doesn't get called because of a runtime
    // error or user cancellation during the startup process.
    event = tictocMsg = nullptr;
}

Txc::~Txc()
{
    // Dispose of dynamically allocated objects
    cancelAndDelete(event);
    delete tictocMsg;
}

void Txc::initialize()
{
    // Create the event object we'll use for delay modeling. Also nullptr the
    // tictocMsg object since we haven't received or sent any yet
    event = new cMessage("event");
    tictocMsg = nullptr;

    // Am I Tic or Toc?
    if (par("sendMsgOnInit").boolValue() == true) {
        // We don't start right away, but instead send a message to ourselves
        // (a `self-message') -- we'll do the first sending when it arrives
        // back to us, at t=5.0s simulated time.
        EV << "Scheduling first send to t=5.0s\n";
        tictocMsg = new cMessage("tictocMsg");
        scheduleAt(5.0, event);
    }

    // Initialize counter. We'll decrement it every time and delete
    // the message when it reaches zero.
    counter = par("limit");

    // The WATCH() statement below will let you examine the variable in GUI.
    WATCH(counter);
}

void Txc::handleMessage(cMessage *msg)
{
    if (msg == event) {
        // The self-message arrived, so we can send out tictocMsg
        EV << "Wait period is over, sending back message\n";

        if (counter == 0) {
            // If counter is zero, delete message. If you run the model, you'll
            // find that the simulation will stop at this point with the message
            // "no more events"
            EV << getName() << "'s counter reached zero, deleting message\n";
            delete tictocMsg;
        } 
        else {
            // Here, we just send it to the other module, through
            // gate `out'. Because both `tic' and `toc' does the same, the message
            // will bounce between the two.
            EV << getName() << "'s counter is " << counter << ", sending back message\n";
            send(tictocMsg, "out");  // send out the message
        }

        // nullptr out tictocMsg so that it doesn't confuse us later
        tictocMsg = nullptr;
    } 
    else {
        // If the message we received is not our self-message, then it must be
        // the tic-toc message arriving from our partner. We remember its
        // pointer in the tictocMsg variable, then schedule our self-message
        // to come back to us in 1s simulated time.
        EV << "Message arrived, starting to wait 1 sec...\n";
        tictocMsg = msg;
        scheduleAt(simTime()+1.0, event);
    }
    counter--;
}

