Wall-clock logs of the experiment runs made in the second phase (solvers/bind on the new benchmarks, the c_slack
sweep, and the agents runs). Format: "<command> rc=<exit code> <seconds>s" or "<time> START/END <job>".

phase1_and_phase2_driver.log   sequential driver: solvers (sokoban2, sokoban3, cube3), bind c_slack 4/2/8, then the
                               first agents step. Its last agents step (sokoban2, 100 episodes) was left running when
                               the driver was stopped; the result file was written at 17:33, no log line was written.
agents_parallel_queue.log      sokoban3 and cube3 agents started 17:28:51 as parallel jobs. cube3 shows rc=127 = it was
                               stopped by the controller at 20:29 after 10811 s without writing a result.
agents_ep300_parallel.log      river and sokoban agents at 300 episodes (parallel).
cube3_agents_reduced_attempt.log  reduced cube3 agents attempt (n = 2, 10 episodes), started 19:34:33; stopped at about
                               20:28 without a result (no END line was written because the job was killed).

The agents runs overlapped each other and development work, so their `seconds` columns are contended; the solvers and
bind runs of the first phase and the new bind/solvers runs ran sequentially (see README, "Provenance").
