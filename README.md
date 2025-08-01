# Task Scheduler Challenge

## Overview

Build a REST API service that manages and executes scheduled tasks. This challenge is designed to assess your system design skills, code quality, testing practices, and understanding of concurrency patterns.

**Estimated Time:** 3-5 hours

## Requirements

### Core Functionality

#### 1. Task Scheduling API
Create a REST API that allows clients to:
- Schedule tasks to run at specified intervals
- Update task intervals for existing scheduled tasks
- Retrieve information about a specific task 
- Retrieve information about upcoming task executions
- View execution history for tasks

#### 2. Task Types
The system should support these four pre-defined task types:

1. **Sleep Task** - Sleeps for a configurable duration (e.g., 2 seconds) and records the time it slept
2. **Counter Task** - Increments a counter value and persists the result to the database
3. **HTTP Task** - Makes a GET request to httpbin.org/status/200 and records response time and status code

#### 3. Task Execution Rules
- **No Self-Overlap**: Each individual scheduled task instance cannot overlap with itself (if Task A with schedule ID 1 is running, it should not start again until the current execution completes)
- **Concurrent Different Tasks**: Multiple different task instances can run simultaneously
- **Interval or Scheduled Execution Support**: Support simple interval scheduling (e.g., "every 30 seconds", "every 2 minutes") or at a specific time in the future (August 8th, 2027 at 17:35:00)
- **Persistent Scheduling**: Task schedules should survive application restarts

#### 4. Required API Endpoints

Your API should provide the following capabilities:

- Schedule a new task with specified type and schedule 
- Update the schedule for an existing task 
- Retrieve information about a specific task  
- Get a list of upcoming task executions 
- List all past task executions with details
- Delete a task

## Technical Requirements

### Technology Stack
Our team uses mostly Python and prefers submissions in python. We also use FastAPI and Postgres and would prefer submissions to be based on this technology stack, however we would value creative and interesting ways to solve this problem that use other languages or databases.

### Using AI
At Trustle we are believers in using AI effectively for all kinds of tasks including writing code. If you use AI, we want to know that you use it effectively. Please document your prompts and techniques you used along the way so that we see how you are utilizing them. 

## Instructions

Fork this repo and commit your solution. You should demonstrate that you can deploy this, either to the cloud or to a local minikube or kind cluster running kubernetes. 

Create a **SOLUTION.md** file that includes:
- Your design decisions and architectural reasoning
- Setup and deployment instructions
- Any trade-offs or assumptions you made
- How you used AI tools to assist with development, including specific prompts or approaches
- Anything else you feel is relevant to understanding your solution

Include all deployment configurations, scripts, or manifests needed to run your solution.

Once you have a working solution, contact careers (at) trustle.com so we can review your submission.

## Evaluation Criteria

We're interested in understanding your thought process and engineering approach, not just the final code. We want to see:
- How you approached the problem and made design decisions
- Your reasoning behind architectural choices
- How you handled trade-offs and constraints
- Evidence of your development process (git commits, testing strategy, etc.)
- Documentation of assumptions and design rationale

## Bonus Points

- Create a client that can be used to call the endpoints of the service
- Graceful handling of application shutdown (completing running tasks)
- Task timeout handling
- Comprehensive logging and monitoring considerations
- Performance considerations and optimizations
- Support for cron-like expressions in addition to simple intervals
- API rate limiting or authentication

## Questions?

If you have any questions about the requirements, please don't hesitate to reach out by sending an email to careers (at) trustle.com

Good luck!
