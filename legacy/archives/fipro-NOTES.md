---
aliases:
  - pages/app to maintain finances
---
# Project Notes

## Program Overview

**Frequency**: Monthly

## Bank Account Flow

- Download transaction history from all 3 banks to date
- Flow starts from **Axis Bank** which is the salary credit account
  - **HDFC Bank**: Used for granular transactions going forward
  - **SBI Bank**: Where more structured transactions are allocated

## Future Considerations

- Go DFS (Digital Financial Services)?
- Annotate PDF for credit card statements
  - Verify and pay
- Budgeting implementation

## Notes

- This document contains personal project notes and development considerations
- For product documentation, see the main README.md

# Timeline
Devlogs
## Phase 1: 
I will try to go from ingesting bank statements and credit card transaction details into a csv file digestable by the goodbudget
- prototyping in python started with my old favourite [[jupyter]] notebooks
	- what is ipykernel? why do other scripting languages not have  such a simple notebook type development setup. [[Mathematica]] also has this
	- similarly even the ipykernel installation took a long time
-  using dataclass for file objects


tech debt
- file io can be made faster with Go
	- https://www.perplexity.ai/search/going-through-the-uplodaded-do-vHK5Ff65TXi93uGBdFPSDw#4


[[2025-08-27]]
- I feel like I left this development just because I started evaluating the switching cost for later and compare that to just making the right decision right now. and when I have to weigh in such decisions, I just end up procrastinating on it
- I am also doing this [[programming]] right now while I am high. 
- It will need 9 basic files always to start with 
	- HDFC 
		- current
		- patch
	- Axis
		- current
		- patch
	- SBI
		- current
		- patch
	- goodbudget current
	- 2 x credit cards
- I need a wallet storage object to store these types
- lo and behold, I ran into circular imports again and this is probably where the criticism of [[Object Oriented Programming]] comes from

[[2025-08-15]]
today's the day we start making the app we had been procrastinating on for so long. I can feel myself getting distracted by the [[Retrieval Augmented Generation|RAG]] project. in fact the rag component could be one part of it.
- we need to start with the requirements for an MVP. am i trying to make believe a sdlc process by trying to make the process tedious.
- one of the major requirements if we want to [[app to maintain finances]], is it will have to be entirely local and do all the magic locally since I can use my paranoia to my advantage here and make sure that pushes me to be as paranoid about these things as possible and not try to resuse some external service like [[supabase]]
-  I should switch to zsh on setup since that is something I am used to now. setup a linux setp script for debian based distribution

[[2025-08-30]]
- we  will be using a minor patch and a major patch. major patch will mostly be monthly since it will consist of the credit card pull as well that ultimately decides the major expenses for the month
- I do not start dividing the script into functions just yet
- do we want to continue working right now with the current kernel configuration or try to understand what is going wrong here
	- can't spend time just side questing and procrastinating on the actual task
	- 
- okay hear me out and this might sound like the craziest idea possible. how about you actually work for 90 minutes and then study for 90 minutes. as [[Feynman]] said. original, chaotic
- My XPS ain't even breaking a sweat yet