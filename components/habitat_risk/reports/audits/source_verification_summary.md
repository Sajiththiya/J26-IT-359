# Source verification audit

Generated (UTC): 2026-10-01T12:39:33.339438+00:00

Source identities remain subject to the evidence recorded in data/metadata/source_registry.csv.
Documentation completeness is not independent source verification.

## Current file checks

                                          check      observed_value
                               Observation rows              102929
                                        Columns                  23
                      Distinct scientific names                  25
                         Exact coordinate pairs                7245
                           Earliest observation 2010-01-01 00:00:00
                             Latest observation 2023-06-17 00:00:00
                      Invalid observation dates                   0
                     Extra exact duplicate rows               18411
Rows in duplicate groups including first copies               31667
                               Missing duration               11401
                               Missing distance               37057
       Nonnumeric or missing observation counts               12743
             Duration greater than 1440 minutes                  20
                      Distinct elevation values                  18
          Rain equals precipitation on all rows                True
                    Loss after observation year                  47
                       Loss in observation year                  37

## Candidate target audit

                                       check  observed_value
             Consecutive location-year pairs            1661
Pairs without loss recorded by starting year            1638
           Recorded next-year positive pairs               0

## Next action

Recover the exact weather/elevation sources and upstream join method, then record supporting evidence in the registry.
