Wall-clock logs of the experiment runs made in the second phase (solvers/bind on the new benchmarks, the c_slack
sweep, and the agents runs). Two line formats: "<command> rc=<exit code> <seconds>s" (driver log) and
"<time> START|END <job> [rc=<exit code> <seconds>s]" (the parallel job logs). Exit codes are those of the python
process as recorded by the wrapper script; an exit code alone does NOT show that a result file was written: the agents
CSV is written only when a benchmark's run ends normally.

phase1_and_phase2_driver.log      sequential driver: solvers (sokoban2, sokoban3, cube3), bind c_slack 4/2/8, then the
                                  first agents step. Its last agents step (sokoban2, 100 episodes) was left running when
                                  the driver was stopped, so no log line exists for it; its result file was written at
                                  about 17:33 (file modification time).
agents_parallel_queue.log         sokoban3 and cube3 agents started 17:28:51 as parallel jobs. sokoban3 ended rc=0 and
                                  wrote its result. cube3 shows "END ... rc=127 10811s" at 20:29:02: that job was stopped
                                  by the controller at about 20:28-20:29 without writing a result file (the meaning of
                                  the code 127 here is not documented; there was no result either way).
agents_ep300_parallel.log         river and sokoban agents at 300 episodes (parallel); both wrote results.
cube3_agents_reduced_attempt.log  reduced cube3 agents attempt (n = 2, 10 episodes): START 19:34:33, "END ... rc=0 3269s"
                                  at 20:29:02, the same second as the other cube3 job's END line, because the controller
                                  stopped both jobs. The rc=0 does NOT mean success: no result file was written (the
                                  step's output file was empty).

The agents runs overlapped each other and development work, so their `seconds` columns are contended; the solvers and
bind runs ran one at a time (see the README sections "Findings" and "Caveats" for the provenance notes).
