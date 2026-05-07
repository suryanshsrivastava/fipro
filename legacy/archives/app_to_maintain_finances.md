- Starting point
	- I need to be able to parse a pdf and load that info into an excel or csv format
	- need to look for an [[Artificial Intelligence|ai]] editor?
		- cursor: already able to extract and parse text from the pdf
	- or should I start raw dogging aka yoloing it from scratch?

tax management
Do I need to look for a better spreadsheet software that might be faster and easier to organise and reference than in Google Sheets

Learn
- [[Model Context Protocol|MCP]] since you want to interact with the google sheets directly as it is a nice place to keep these documents
- Need a local secrets storage system for all these passwords and other credentials other than freaking markdown files
	- since we will be building this we either need some mock credentials or we need to restrict ourselves to open source/local -first solutions which will give you better control and more learning. 
	- can you break the captcha

Perplexity Deep Research Prompt:
Analyze my credit card statements from past few months and create a detailed report detailing expenses, their purpose and date etc. in the format of a bank statement attached to keep the consistency.

<idea>
Can a collection of prompts for different purposes be treated like an app. is that what an [[Model Context Protocol|MCP]] does?
</idea>

- One  place where android has an edge is sms based expense trackign that is alllowed in the ecosystem for ease. maybe I can make a similar app with the dump of messages I recieve
	- Do I need daily tracking of each expense? or can I just make do with the weekly updates to the csv by appending
	- Keep revising the IIIT curriculum
		- with the proper reading material and everything
		- do I need access to courses.iiit.ac.in?
		- 

Competition Research:
- https://app.formulabot.com/bank-statement-converter-pdf-to-excel
- What we are looking for here is a goddamn envelope based budgeting app: goodbudget
- llmwhisperer is exactly what I need but for free

I used llmwhisper to extract layout preserving txt file using 


extract all 329 entries from the ocr text file @extracted_transations.txt handling different scenarios  
1. eg. particulars wrapping over the previous line and the current line  
2. the last column Int.Br is an enum with only values 2177, 248 or 100 (whole match not part of other words)  
3. this also demonstrates the very subtle demarcation between debit/credit columns and their mutually exclusivity and also its vicinity to the balance column.  
I will keep telling you more rules as we iterate over the output.csv file.  
  
here's the lld I have in mind.  
4. module/function for first demarcate the lines belonging to same row using (2). now we have multiple lines mapped to each row.  
now for each row  
# Validation1:  
should be 329 of such lists of lists of lines for validation  
  
2. module/function where we go through the list of list of lines and realise we can easily make the rows for the csv file by picking value of each column except that "particulars" column will have text from all the lines in the list of lines for a particular row. we can see example in validations  
# Validation2: check the csv file rows for 1st and last line:  
Sample rows of csv for validation and testing  
Header row: [ Tran Date, Chq No, Particulars, Debit, Credit, Balance, Init. Br]  
UPI/P2A/309500015040/SURYANSH /State  
05-04-2023 Ban/NA 111.00 111.00 2177  
Sample first Credit transaction: [ "05-04-2023" ,, "UPI/P2A/309500015040/SURYANSH /State Ban/NA,", 111.00, 111.00, 2177 ]  
  
NEFT/CITIN25539139995/CAPITAL ONE  
26-03-2025 SERVICES (I) PVT/CITI BANK/ 206170.53 540131.16 248  
Sample last debit transaction: [19-03-2025.. "UPI/P2A/544447433135/SURYANSH SRIVASTAVA /UPI/HDFC BANK LTD", 49900.00,, 338960.63, 2177 ]  
particulars should be the exact string (parts on different lines joined by spaces)  
  
keep iterating atleast until the above 2 validation checkpoints pass (print the results) rows EXACTLY match

to take the flow further and the habit to set the frequency of execution
- for now I am going to take axis the manual route until this import thing works on the app.
- 

Limitations with Wallet app
- Transfers are handled weirdly and diffcult to reconcile. leads to a lot of duplicates and thorws off the calcualtion: 
	- workaround for the meantime. 
		- use outside of wallet as a proxy. maybe it will be easier to reconcile later
		- or just delete from the axis one because you can without losing the original state
- Worth considering to turn the entire workflow into manual csv upload to make it more editable
- Also worth considering making a clone of this app: seems like a solid idea

We can take a lot of learnings from the wallet app. It is far from perfect but definitely doable for the time being
Use it for a month atleast before iterating any further
- make another account on wallet for archival purposes

I need to make a voice activated budgeting partner

we need a 
## git for finances

git sync
- [[Finances#^df25f3]]


---


I am sure I have recorded somewhere the current state of the project along with the next steps and if not we should fix the [[RAG Project]]
we can use the [[smart connections]] [[Obsidian]] plugin as a proxy for it as of now

before all that, I think I will start with consolidating all the data in a single file and maybe make an interface that when fed this newly downloaded file (as it does not currently have the ability to download these files themselves). 

even before that I need to [[setup a local LLM server]]

use [[Vite]] or [[vue]] for frontend to feel the difference with [[React]] that you used to develop in earlier

we will continue using [[WSL]] for now. as much as there are painpoints to using [[Windows]]. we will document it on the page [[Switching to Linux]] though so that I have a clear answer to tell myself and people when asked why linux

https://www.youtube.com/watch?v=BvCOZrqGyNU

Local Stack:
1. [[Windows]]
2. [[WSL]]
3. [[Docker]]
4. AI Models
	- Granite
	- [[Llama]]
- open web ui
- vpn
- [[NAS]] system

[[Perplexity]] my default search engine for the next few days
--


I am sure I have recorded somewhere the current state of the project along with the next steps and if not we should fix the [[RAG Project]]
we can use the [[smart connections]] [[Obsidian]] plugin as a proxy for it as of now

before all that, I think I will start with consolidating all the data in a single file and maybe make an interface that when fed this newly downloaded file (as it does not currently have the ability to download these files themselves). 

even before that I need to [[setup a local LLM server]]

use [[Vite]] or [[vue]] for frontend to feel the difference with [[React]] that you used to develop in earlier

we will continue using [[WSL]] for now. as much as there are painpoints to using [[Windows]]. we will document it on the page [[Switching to Linux]] though so that I have a clear answer to tell myself and people when asked why linux

https://www.youtube.com/watch?v=BvCOZrqGyNU

Local Stack:
1. [[Windows]]
2. [[WSL]]
3. [[Docker]]
4. AI Models
	- Granite
	- [[Llama]]
- open web ui
- vpn
- [[NAS]] system

[[Perplexity]] my default search engine for the next few days

[[AI Agents]]
- Gemini CLI
- Claude Code
- Opencode

Need to get wrist supports to avoid fatigue

using gemini as my go to online api, since google sort of already has all of my data available if they want it. over the years, I have really leaned into the  whole google ecosystem. with like 4 gmail accounts:
- suryansh.intel@gmail.com
- suryansh.srivastava99@gmail.com
- suryanshsrvstv42@gmail.com
- fawkes41.99@gmail.com

I need to keep my data limited to the high security suryansh.srivastava99@gmail.com this is going to be my blue fortified account and hoping google spends enough of their resources to make sure apart from some good old stupidity, I won't leak my credentials to AI even while using them within my files. seems suspicious.


I am testing out these cli agents instead of:
- [[opencode]]
- [[Gemini#CLI]] 


Embrace | Extend | Extinguish

[[2025-08-20]]
# [[Decision Logs]]
- Dataclasses vs Dictionary
- Pandas vs Polars

why did I choose Python for this project. claude actually defaulted to it
if i am using python to wrangle with data I would prefer a jupyter notebook rather than a waiting for the entire file to compile and make the jupyter notebook as the source of truth for the code. a script or a tool to always keep your notebook in sync with the exported python script. 

[[2025-08-23]]
today I consolidate. that's the name of the game for today. 
etymology of the word consolidate

---
# Fi-Proova

A one stop dashboard for all my personal finance management
## Overview
