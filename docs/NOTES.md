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

edited in obsidian

edited in cursor

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
- 