# Report for assignment 4

## Project

Name: Piqueserver

URL: [https://github.com/piqueserver/piqueserver](https://github.com/piqueserver/piqueserver)

A server implementation for the game Ace of Spades 0.75. Piqueserver further extends PySnip, an older, inactive server project.

## Complexity

## Coverage

# Before the changes

============================= test session starts ==============================
platform linux -- Python 3.6.3, pytest-3.4.0, py-1.5.2, pluggy-0.6.0
rootdir: /home/safe/Code/kth/sofeng/piqueserver, inifile:
plugins: cov-2.5.1
collected 65 items                                                             

tests/piqueserver/test_commands.py ....                                  [  6%]
tests/piqueserver/test_config.py ...........                             [ 23%]
tests/piqueserver/test_networkdict.py .......                            [ 33%]
tests/piqueserver/test_player.py .                                       [ 35%]
tests/piqueserver/test_run.py ....                                       [ 41%]
tests/piqueserver/test_server.py .                                       [ 43%]
tests/piqueserver/test_statistics.py ..                                  [ 46%]
tests/pyspades/test_bytes.py .....                                       [ 53%]
tests/pyspades/test_common.py ....                                       [ 60%]
tests/pyspades/test_constants.py .                                       [ 61%]
tests/pyspades/test_mapgenerator.py .........x....                       [ 83%]
tests/pyspades/test_player.py .                                          [ 84%]
tests/pyspades/test_protocol.py .                                        [ 86%]
tests/pyspades/test_server.py .                                          [ 87%]
tests/pyspades/test_types.py ......x.                                    [100%]

----------- coverage: platform linux, python 3.6.3-final-0 -----------
Name                                      Stmts   Miss Branch BrPart  Cover
---------------------------------------------------------------------------
piqueserver/__init__.py                       1      0      0      0   100%
piqueserver/__main__.py                       3      3      2      0     0%
piqueserver/banpublish.py                    25     25      4      0     0%
piqueserver/bansubscribe.py                  36     36     10      0     0%
piqueserver/cfg.py                           10      0      0      0   100%
piqueserver/commands.py                     193    146     76      0    20%
piqueserver/config.py                       123      0     32      0   100%
piqueserver/console.py                       58     42     16      1    23%
piqueserver/core_commands/__init__.py         8      0      0      0   100%
piqueserver/core_commands/game.py           138    118     46      0    11%
piqueserver/core_commands/info.py            28     22     16      0    14%
piqueserver/core_commands/map.py             49     40      4      0    17%
piqueserver/core_commands/moderation.py     170    141     36      0    14%
piqueserver/core_commands/movement.py       141    120     62      0    10%
piqueserver/core_commands/player.py          60     49     26      0    13%
piqueserver/core_commands/server.py          32     25      8      0    18%
piqueserver/core_commands/social.py          38     34     24      0     6%
piqueserver/irc.py                          229    229     58      0     0%
piqueserver/map.py                           94     71     18      0    21%
piqueserver/networkdict.py                   56     14     18      1    74%
piqueserver/player.py                       300    239    170      0    13%
piqueserver/run.py                          121     91     50      3    23%
piqueserver/scheduler.py                     30     21      8      0    24%
piqueserver/server.py                       573    446    188      0    17%
piqueserver/ssh.py                           43     43      4      0     0%
piqueserver/statistics.py                   109     53     22      4    47%
piqueserver/statusserver.py                  72     72     10      0     0%
piqueserver/version.py                        2      0      0      0   100%
piqueserver/web/__init__.py                   0      0      0      0   100%
pyspades/__init__.py                          7      0      0      0   100%
pyspades/client.py                          103    103     30      0     0%
pyspades/collision.py                        17     12      0      0    29%
pyspades/color.py                            39     39     16      0     0%
pyspades/constants.py                        39      0      0      0   100%
pyspades/debug.py                            40     24     14      0    30%
pyspades/entities.py                        124     92     32      0    21%
pyspades/mapgenerator.py                     63      0     16      1    99%
pyspades/master.py                           66     41     10      0    33%
pyspades/player.py                         1002    829    428      0    12%
pyspades/protocol.py                        120     92     34      0    18%
pyspades/server.py                          288    199     98      0    23%
pyspades/team.py                             70     50     24      0    21%
pyspades/tools.py                            22     20      4      0     8%
pyspades/types.py                            53      2     10      0    97%
pyspades/weapon.py                          109     56     24      0    40%
setup.py                                     45     45     16      0     0%
tests/__init__.py                             0      0      0      0   100%
tests/piqueserver/__init__.py                 0      0      0      0   100%
tests/piqueserver/test_commands.py           21      4      0      0    81%
tests/piqueserver/test_config.py            132      0      2      0   100%
tests/piqueserver/test_networkdict.py        37      2      6      0    95%
tests/piqueserver/test_player.py              5      0      0      0   100%
tests/piqueserver/test_run.py                51      0      0      0   100%
tests/piqueserver/test_server.py              5      0      0      0   100%
tests/piqueserver/test_statistics.py         31      2      0      0    94%
tests/pyspades/__init__.py                    0      0      0      0   100%
tests/pyspades/test_bytes.py                 40      0     10      0   100%
tests/pyspades/test_common.py                15      0      2      0   100%
tests/pyspades/test_constants.py              6      0      0      0   100%
tests/pyspades/test_mapgenerator.py         119     11     14      0    89%
tests/pyspades/test_player.py                 6      0      0      0   100%
tests/pyspades/test_protocol.py               6      0      0      0   100%
tests/pyspades/test_server.py                 6      0      0      0   100%
tests/pyspades/test_types.py                 58      2      0      0    97%
---------------------------------------------------------------------------
TOTAL                                      5487   3705   1698     10    27%

# After the changes

TODO: new coverage report here

===================== 63 passed, 2 xfailed in 2.47 seconds =====================

### High cyclomatic complexity functions

We used lizard to generate the cyclomatic complexety for each function in the project and then chose the top 10.

1. `piqueserver::scripts::badmin.py::score_grief()` (CCN = 39)  
The `badmin.py` module is a bot that do some common administrative tasks, This particular function tries to set a score a players behaviour on the server in terms of player behaviour. It does so by looking at and combining various metrics like for how long the player has been playing, how many of their teammates blocks the player has destroyed and so forth. Higher score means the player might be harassing other players. Right now this is done with numerous `if/else` statements combined with a couple of `for`-loops. Complexity is probably needlessly high since a lot of this functionality could be summarized as mathematical functions instead.

   `score_grief()` returns a score, the different possible branches will only affect what the score will be. If the player hasn't destroyed any blocks at all, though, the function will exit early and return 0. Otherwise it will calculate a score and return it and simultaneously print some statistics. The statistics printed aside, the function has no side effects.

2. `piqueserver::scripts::blockinfo.py::grief_check()` (CCN = 38)  
This is an admin command that prints information about player interaction with blocks. The idea is to give some metrics about behaviour that can be used to infer if the player is griefing. The cyclomatic complexity is high since a lot of `if`-statements are used to format the string returned from the function. For example one such statement prints "minute" or "minutes" depending whether it had passed less than one minute or more since the player last removed a block. It's reasonable for the CCN to be high here, building strings are one of those things that's hard to do differently.

   `grief_check()` returns a string with potentially a lot of information. Each part of the string has been crafted by using `if/elif/else` which is the (almost) sole cause for the high cyclomatic complexity (there are two cases where list comprehension are used too). Depending on the players behaviour the string might be very long or very short, but a string will always be returned and there will be no side effects.

3. `piqueserver::server::FeatureProtocol::__init__()` (CCN = 29)  
The constructor of one of the main classes of the whole project. The complexity arises from a few different reasons:
    * Configuration files are read from disk and exceptions has to be handled.
    * After reading configuration files it parses options in one of them.
    * The class inherits from `pyspades::server.py::ServerProtocol` and changes a couple of internally used configuration parameters to a new format.

   Complexity that arises from the `try/except` blocks are probably needed since exception handling is very much needed when doing I/O. That said they could probably be grouped together. The complexity from the `if`-statements used when reading configuration files and setting member variables, loading modules, and so forth, depending on whether something is present in the configuration or not, are not ideal.

   `FeatureProtocol` is one of the larger classes in the project and it's constructor is a bit messy. It's unfeasible to describe each possible state it could be in depending on what branches are taken. Like the name of the class hints, a lot of stuff in the constructor concerns different features, for example if the server should have an IRC Relay, if it should have SSH enabled, if the it should be published and so forth. There are also a so-called ban list read from file and a map are loaded (which also might be read from disk). All in all, most branches will result in a `FeatureProtocol` object in a valid state with various enabled or disabled features, but some paths (I/O error, map loading error and an erroneous game mode) might lead to an exception being thrown.

4. `pyspades::player::on_block_action_recieved()` (CCN = 25)  
The validity of player block construction and destruction are checked here. A lot of conditions has to be fulfilled for a block to be placed or destroyed. These checks are done in nested `if/else` statements. Due to the nature of this code, cyclomatic complexity are expected to be high but the current implementation could probably be refactored to lower it a bit.

   Depending on what branches are taken in `on_block_action_recieved()` a block will either be placed in the world, destroyed in the world or nothing will happen. In the case where a block are destroyed, a block might be added to the players inventory. Likewise in the case where a block is placed in the world, a block will be removed from the players inventory.

5. `pyspades::client::loader_received()` (CCN = 20)  
Loaders handles various network related stuff, like streaming a map from the server to the client or player position updates. Basically the function takes a domain specific packet as input and handles it. There seems to be a lot of unused code (`if` statements followed by `pass`) which could be removed to lower complexity, but in general, the way the project works now, it needs to be high. However, even though the function evidently handles packets, a lot of the complexity arises from printing messages that look a lot like debug messages. 

   `loader_received()` will either load a map in the client (there are two different kind of map loaders, each will result in a map), print a lot of stuff and then do nothing or just do nothing, depending on which branches are taken.

6. `pyspades::player::on_position_update_recieved()` (CCN = 20)  
Called when a player changes position. A lot of checks has to be made both in regards of the validity of the new position and the consequences. For example, if the game are a capture the flag game, and the new position is close enough to capture the enemy flag, trigger that functionality. High complexity is, perhaps not necessary, but at least motivated from the functionality since there are a lot of different parameters to take into account when moving a player.

   `on_position_update_recieved()` affects the player which will either move or not move to the new position depending on a lot of factors, for example if the new position is blocked or the server has deemed the player a hacker. If the new position contains the enemy flag and the game are in capture the flag mode, the flag will be picked up the player. If the game are in territory control mode and an enemy territory is close enough, the player will start capturing that territory.

7. `pyspades::player::grenade_exploded()` (CCN = 20)  
Handles grenade explosion. Not much to say, the function checks if the location if the grenade is valid (which, presumably, has been thrown earlier). It then checks if players are hit and how the hit will affect them, and if the world is hit, it checks which voxels are affected and removes them. Complexity seems to be needlessly high (there's a lot of `continues`) and could be lowered by, for example, implementing a `player.py::hit_by_grenade`-method or similar.

   Possible outcomes of `grenade_exploded()` are that hit players are killed, have their hp decreased or remain as they were in case they are already dead. Voxels that are hit by the blast are removed.

8. `pyspades::player::on_input_data_recieved()` (CCN = 19)  
Sends updates about the players input in terms of movement to other players. Again, some checks in terms of the validity of the action is done. Like the above, complexity could probably be lowered but is not needlessly high. There are plenty of code that has been commented away, leaving some functionality unreachable/unimplemented.

   There are a lot of possible outcomes from this `on_input_data_recieved()`, but most of them will result in the transmission of a/several packet(s) to the other players with information about the players current movement actions. These actions are dependant on the input and are, for example, sneak, jump, walk and so on. If the player is either dead or some flags concerning player visibility are set, no packet will be transmitted.

9. `piqueserver::run::main()` (CCN = 16)  
The entry point to the server program which parses a lot of command line arguments and configuration files. There are some redundant `if`-statement but generally, complexity is inherently high. Command line argument parsing (and handling) could be delegated to a library or handled by, for example, a dict of functions, which might lower the cyclomatic complexity.

   `main()` will initialize the server from some configuration files and command line arguments. Depending on the arguments, the provided configuration files might copied. The server will always be started, no matter what branch, except for the case when an exception is thrown if the configuration file are in an unknown format.

10. `piqueserver/server.py/run()` (CCN = 14)  
Starts the server. Like the `FeatureProtocol` constructor, most of the cyclomatic complexity here arises from file IO (and the `try/except` associated with them) and probably should be left as it is. The actual complexity is not overwhelming. There seems to be a lot of redundancy though. For example, the configuration file seems to be validated even though it already got validated in `piqueserver::run::main()` (which calls this function before terminating).

    The only possible result of `run()` are that a game server either is started or are not, which will be the case of any of the numerous `try/except` blocks generates an exception, in which case the program might get shut down. The properties of the server are defined in the configuration file, but might get modified during execution of `run()`. For example, if a script are to be loaded but aren't available on the server, the script is ignored.

#### Possible refactorizations 

1. `piqueserver::scripts::badmin.py::score_grief()` One obvious refactorizations would be something like
   ```python
   gscore += static_team_blocks(team_blocks)
   gscore += team_block_ratio(team_blocks, total_blocks)
   ```
   where `static_team_blocks` and `team_block_ratio` would be functions that simplified line 131 to 152. This would eliminate 10 `if/elif`-statements

2. `piqueserver::scripts::blockinfo.py::grief_check()` This function could be considerably less complex if the result was just the numbers instead of a string describing the implication of the numbers. I.e., we could just print the metrics from which the string are generated and be done with it. Refactoring out functions as it is now makes little sense (in my humble opinion) but could be done by replacing `if/else`-statements that apply formatting (like the minute/minutes) with functions.

   Similarly, each part of the string could be a function so, for example, the part that deals with generating name-strings that are colored or not depending on input parameters would just be
   ```python
   names = get_names(infos, colored=True)
   ```
   and the part that adds block-placement to the string would be 
   ```python
   message += get_block_placement(names, colored=True)
   ```
   and so on. This would probably remove most of the cyclomatic complexity of this function.

3. `piqueserver::server::FeatureProtocol::__init__()` Using proper serialization would reduce a lot of the cyclomatic complexity here. Otherwise, the problem is that each property read from the configuration file has to be verified. Often there are also imports associated with an activated feature in the server. We cold do all the imports in the top of the file (as usual) and create a function for each feature of the `FeatureProtocol` that has to be verified by an `if`-statement:
   ```python
   self.ban_publish = self.__set_ban_publish(self, config)
   self.ban_subscribe = self.__set_ban_subscribe(self, config)
   ```

4. `pyspades::player::on_block_action_recieved()` There are some issues that could be addressed as follows
    * the interval is needlessly complex, it could be a single function examining the equipment of the player
      ```python
      interval = self.__get_interval(self, contained)
      ```
    * The same goes for the `rapid_hack_detect`-routine
      ```python
      probable_rapid_hack = self.__get_probable_rapid_hack(self, last_time, current_time)
      if probable_rapid_hack:
          print('RAPID HACK:', self.rapids.window)
          self.on_hack_attempt('Rapid hack detected')
          return
      ```
    * for the "build block" and "remove block" actions we could do something like
      ```python
      if value == BUILD_BLOCK and self.__valid_build_block(self, pos, contained)
          self.on_block_build(x, y, z)
      elif value == DESTROY_BLOCK and self.__valid_destroy_block(self, pos, contained)
          count = map.destroy_point(x, y, z)
      ```
      where the private methods performed the checks for that now takes that many `if/elif/else`-statements

6. `pyspades::player::on_position_update_recieved()`
    Split the main part of the function in to two depending on what game mode we are running:
    ```python
    if game_mode == CTF_MODE:
        self.__handle_CTF_MODE(self, contained)
    elif game_mode == TC_MODE:
        self.__handle_TC_MODE(self, contained) 
    ```

### Tools

### DIY

Initially we had some issues regarding what you should actually count when calculating
the complexity by hand. Some of the questions we had were:

* Does `sys.exit(code)` count as an exit point?
* Do exceptions count as exit points?
* Do if-statements with multiple clauses count as one of more decisions?
* Does `with` count as a decision.

Once we knew the answers to these, we all got the same results as each other and
that of Lizard.

### Evaluation

## Effort spent

|                     |Jonas|David|Safir|Robert|Fredrik|
|---------------------|-----|-----|------|------|-------|
|Planning             |     |     |   2  |      |    1  |
|Discussions          |     |     |   2  |      |    4  |
|Reading documentation|     |     |   0  |      |    1  |
|Configuration        |     |     |   0  |      |       |
|Analyzing code/output|     |     |   3  |      |    2  |
|Writing documentation|     |     |   3  |      |    6  |
|Writing code         |     |     |   4  |      |    6  |
|Running code         |     |     |   2  |      |       |

## Overall experience

Getting to investigate new metrics for evaluating the complexity of a function is indeed interesting and brings perspective to what makes functions more complex to test and cover. It is quite fulfilling to write tests when there are test coverage tools to analyze how efficiently the code is tested. Using lizard was very straight forward and intuitive and the tool displays information in a clean and understandable way. All in all, every group member got their fair share of mocking tests and improving on the test coverage.
