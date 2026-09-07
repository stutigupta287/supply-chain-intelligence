"""Interactive CLI REPL for GenAI assistant."""
import logging
from .llm import llm_with_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def run_repl():
    """Run interactive REPL for supply chain questions."""
    print("=== Supply Chain GenAI Assistant ===")
    print("\nExample questions:")
    print("  • What is the on-time rate for shipments from Shanghai to Rotterdam?")
    print("  • Which routes have the highest average delay?")
    print("  • What is the delay risk for shipment SHP-00421?")
    print("\nCommands: exit, quit, help\n")
    
    while True:
        try:
            user_input = input(">> ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            
            if user_input.lower() == "help":
                print("Ask questions about supply chain routes and shipments.")
                print("The assistant can answer questions about route statistics,")
                print("on-time rates, delays, and shipment information.")
                continue
            
            if not user_input:
                continue
            
            logger.info(f"\n💬 User Question: {user_input}")
            logger.info("🤖 LLM Processing...")
            
            # Call LLM with user input
            response = llm_with_tools.invoke(user_input)
            
            # Check if tool was called
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"✓ LLM Decision: Call tool '{response.tool_calls[0]['name']}'")
                logger.info(f"📝 Tool Arguments: {response.tool_calls[0]['args']}")
                
                # Execute tool calls
                from langchain_core.messages import ToolMessage
                
                tool_results = []
                for tool_call in response.tool_calls:
                    if tool_call["name"] == "get_route_stats":
                        from .tools import get_route_stats
                        result = get_route_stats.invoke(tool_call["args"])
                        tool_results.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call["id"]
                            )
                        )
                
                logger.info("🤖 LLM Generating final response...")
                # Get final response with tool results
                messages = [
                    {"role": "user", "content": user_input},
                    response,
                ] + tool_results
                
                final_response = llm_with_tools.invoke(messages)
                logger.info(f"✓ Final Response Generated\n")
                print(f"\n{final_response.content}\n")
            else:
                # Direct response without tool call
                logger.info("✓ LLM responded without tool call\n")
                print(f"\n{response.content}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")
