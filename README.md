::

              __       __    __
    .--.--.--|__.-----|  |--|  |--.-----.-----.-----.
    |  |  |  |  |__ --|     |  _  |  _  |     |  -__|
    |________|__|_____|__|__|_____|_____|__|__|_____|
                                       version 2.1.2

    Build composable event pipeline servers with minimal effort.


    ===================
    wishbone.output.sse
    ===================

    Version: 1.0.0

    Serve event data as server sent events.
    ---------------------------------------


        Serve event data as server sent events.

        When the event header contains:

        If nobody is consuming events then they're lost.
        If <show_last> is set to True, then the last known value
        can be consumed by the client.

        Parameters:

            - selection(str)("@data")
               |  The part of the event to submit externally.
               |  Use an empty string to refer to the complete event.

            - bind(string)("0.0.0.0")
               |  The address to bind to.

            - port(int)(19283)
               |  The port to bind to.

            - show_last(bool)(False)
               |  If true submits the last known value to
               |  a new connection.

            - keepalive(bool)(False)
               |  If true sends a keepalive message at
               |  <keepalive_interval> seconds.

            - keepalive_interval(int)(False)
               |  The time in seconds to send keep-alive
               |  messages to the client.

            - destination(str)("")*
               |  The endpoint from which the event can be consumed.


        Queues:

            - inbox
               |  Incoming events submitted to the outside.


