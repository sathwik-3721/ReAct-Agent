from src.tools.serp import search as google_search
from src.tools.wiki import search as wiki_search
from google.generativeai import GenerativeModel
from src.utils.io import write_to_file
from src.config.logging import logger
from src.config.setup import config
from src.llm.gemini import generate
import google.generativeai as genai
from src.utils.io import read_file
from pydantic import BaseModel
from typing import Callable, Optional
from pydantic import Field
from typing import Union
from typing import List
from typing import Dict
from enum import Enum
from enum import auto
import json
import time


Observation = Union[str, Exception]

PROMPT_TEMPLATE_PATH = "./data/input/react.txt"
OUTPUT_TRACE_PATH = "./data/output/trace.txt"


class Name(Enum):
    """
    Enumeration for tool names available to the agent.
    """
    WIKIPEDIA = auto()
    GOOGLE = auto()
    NONE = auto()

    def __str__(self) -> str:
        """
        String representation of the tool name.
        """
        return self.name.lower()


class Choice(BaseModel):
    """
    Represents a choice of tool with a reason for selection.
    """
    name: Name = Field(..., description="The name of the tool chosen.")
    reason: str = Field(..., description="The reason for choosing this tool.")


class Message(BaseModel):
    """
    Represents a message with sender role and content.
    """
    role: str = Field(..., description="The role of the message sender.")
    content: str = Field(..., description="The content of the message.")


class Tool:
    """
    A wrapper class for tools used by the agent, executing a function based on tool type.
    """

    def __init__(self, name: Name, func: Callable[[str], str]):
        """
        Initializes a Tool with a name and an associated function.

        Args:
            name (Name): The name of the tool.
            func (Callable[[str], str]): The function associated with the tool.
        """
        self.name = name
        self.func = func

    def use(self, query: str) -> Observation:
        """
        Executes the tool's function with the provided query.

        Args:
            query (str): The input query for the tool.

        Returns:
            Observation: Result of the tool's function or an error message if an exception occurs.
        """
        try:
            return self.func(query)
        except Exception as e:
            logger.error(f"Error executing tool {self.name}: {e}")
            return str(e)
class IterationStep(BaseModel):
    """Represents a single step in the agent's reasoning process."""

    iteration_number: int = Field(..., description="The iteration number.")
    thought: Optional[str] = Field(None, description="The agent's thought process.")
    action: Optional[Dict] = Field(None, description="The action taken by the agent.")
    observation: Optional[str] = Field(None, description="The observation made by the agent.")
    final_answer: Optional[str] = Field(None, description="The final answer if this is the last step")
    error: Optional[str] = Field(None, description="Error message if error occurs")

class Agent:
    """
    Defines the agent responsible for executing queries and handling tool interactions.
    """

    def __init__(self, model: GenerativeModel) -> None:
        """
        Initializes the Agent with a generative model, tools dictionary, and a messages log.

        Args:
            model (GenerativeModel): The generative model used by the agent.
        """
        self.model = model
        self.tools: Dict[Name, Tool] = {}
        self.messages: List[Message] = []
        self.query = ""
        self.max_iterations = 5
        self.current_iteration = 0
        self.template = self.load_template()
        self.trace_iterations: List[IterationStep] = []

    def load_template(self) -> str:
        """
        Loads the prompt template from a file.

        Returns:
            str: The content of the prompt template file.
        """
        return read_file(PROMPT_TEMPLATE_PATH)

    def register(self, name: Name, func: Callable[[str], str]) -> None:
        """
        Registers a tool to the agent.

        Args:
            name (Name): The name of the tool.
            func (Callable[[str], str]): The function associated with the tool.
        """
        self.tools[name] = Tool(name, func)

    def trace(self, role: str, content: str, current_iteration_step: IterationStep = None) -> None:
        """
        Logs the message with the specified role and content and stores the iteration step.

        Args:
            role (str): The role of the message sender.
            content (str): The content of the message.
            current_iteration_step (IterationStep, optional): The step to be updated.
        """
        if role != "system":
            self.messages.append(Message(role=role, content=content))
        if current_iteration_step is not None:
            self.trace_iterations.append(current_iteration_step)
        else:
          write_to_file(path=OUTPUT_TRACE_PATH, content=f"{role}: {content}\n")

    def get_history(self) -> str:
        """
        Retrieves the conversation history.

        Returns:
            str: Formatted history of messages.
        """
        return "\n".join([f"{message.role}: {message.content}" for message in self.messages])

    def think(self) -> None:
        """
        Processes the current query, decides actions, and iterates until a solution or max iteration limit is reached.
        """
        self.current_iteration += 1
        logger.info(f"Starting iteration {self.current_iteration}")
        current_iteration_step = IterationStep(iteration_number=self.current_iteration)
        write_to_file(path=OUTPUT_TRACE_PATH, content=f"\n{'='*50}\nIteration {self.current_iteration}\n{'='*50}\n")

        if self.current_iteration > self.max_iterations:
            logger.warning("Reached maximum iterations. Stopping.")
            error_message = "I'm sorry, but I couldn't find a satisfactory answer within the allowed number of iterations. Here's what I know so far: " + self.get_history()
            current_iteration_step.error = error_message
            self.trace("assistant", error_message, current_iteration_step)
            return

        prompt = self.template.format(
            query=self.query,
            history=self.get_history(),
            tools=', '.join([str(tool.name) for tool in self.tools.values()])
        )

        response = self.ask_gemini(prompt)
        logger.info(f"Thinking => {response}")
        current_iteration_step.thought = f"Thought: {response}"
        self.trace("assistant", f"Thought: {response}",current_iteration_step)
        self.decide(response, current_iteration_step)

    def decide(self, response: str, current_iteration_step: IterationStep) -> None:
        """
        Processes the agent's response, deciding actions or final answers.

        Args:
            response (str): The response generated by the model.
        """
        try:
            cleaned_response = response.strip().strip('`').strip()
            if cleaned_response.startswith('json'):
                cleaned_response = cleaned_response[4:].strip()

            parsed_response = json.loads(cleaned_response)

            if "action" in parsed_response:
                action = parsed_response["action"]
                tool_name = Name[action["name"].upper()]
                current_iteration_step.action = action
                if tool_name == Name.NONE:
                    logger.info("No action needed. Proceeding to final answer.")
                    self.think()
                else:
                    self.trace("assistant", f"Action: Using {tool_name} tool", current_iteration_step)
                    self.act(tool_name, action.get("input", self.query), current_iteration_step)
            elif "answer" in parsed_response:
                current_iteration_step.final_answer = f"Final Answer: {parsed_response['answer']}"
                self.trace("assistant", f"Final Answer: {parsed_response['answer']}", current_iteration_step)
            else:
                raise ValueError("Invalid response format")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {response}. Error: {str(e)}")
            current_iteration_step.error = f"I encountered an error in processing. Let me try again. Error: {str(e)}"
            self.trace("assistant", current_iteration_step.error, current_iteration_step)
            self.think()
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            current_iteration_step.error = f"I encountered an unexpected error. Let me try a different approach. Error: {str(e)}"
            self.trace("assistant", current_iteration_step.error, current_iteration_step)
            self.think()

    def act(self, tool_name: Name, query: str, current_iteration_step: IterationStep) -> None:
        """
        Executes the specified tool's function on the query and logs the result.

        Args:
            tool_name (Name): The tool to be used.
            query (str): The query for the tool.
            current_iteration_step (IterationStep): The current iteration step to be updated.
        """
        tool = self.tools.get(tool_name)
        if tool:
            result = tool.use(query)
            observation = f"Observation from {tool_name}: {result}"
            current_iteration_step.observation = observation
            self.trace("system", observation, current_iteration_step)
            self.messages.append(Message(role="system", content=observation))  # Add observation to message history
            self.think()
        else:
            logger.error(f"No tool registered for choice: {tool_name}")
            current_iteration_step.error = f"Error: Tool {tool_name} not found"
            self.trace("system", current_iteration_step.error, current_iteration_step)
            self.think()

    def execute(self, query: str) -> List[IterationStep]:
        """
        Executes the agent's query-processing workflow.

        Args:
            query (str): The query to be processed.

        Returns:
            List[IterationStep]: All iteration steps.
        """
        self.query = query
        self.trace_iterations.clear()
        self.messages.clear()
        self.current_iteration = 0

        self.trace(role="user", content=query, current_iteration_step=None)
        self.think()
        return self.trace_iterations

    def ask_gemini(self, prompt: str) -> str:
        """
        Queries the generative model with a prompt.

        Args:
            prompt (str): The prompt text for the model.

        Returns:
            str: The model's response as a string.
        """
        response = generate(self.model, [prompt])  # Pass prompt as a list of strings
        time.sleep(2)
        return str(response) if response is not None else "No response from Gemini"


def run(query: str) -> str:
    """
    Sets up the agent, registers tools, and executes a query.

    Args:
        query (str): The query to execute.

    Returns:
        str: The agent's final answer.
    """
    # configure the Gemini API key
    genai.configure(api_key=config.GEMINI_API_KEY)

    # initialize gemini model
    gemini = genai.GenerativeModel(model_name=config.MODEL_NAME)  # Initialize Gemini model

    agent = Agent(model=gemini)
    agent.register(Name.WIKIPEDIA, wiki_search)
    agent.register(Name.GOOGLE, google_search)

    answer = agent.execute(query)
    return "test"


#  Added Code below
# Initialize the agent and register tools
genai.configure(api_key=config.GEMINI_API_KEY)
gemini = genai.GenerativeModel(model_name=config.MODEL_NAME)
agent = Agent(model=gemini)
agent.register(Name.WIKIPEDIA, wiki_search)
agent.register(Name.GOOGLE, google_search)

if __name__ == "__main__":
    query = "What is the age of the oldest tree in the country that has won the most FIFA World Cup titles?"
    final_answer = run(query)
    logger.info(final_answer)
