from pydantic_ai import Agent

chatbot_agent = Agent('openai:gpt-5-nano',system_prompt="You answer concise.")

# result1 = chatbot_agent.run_sync("My name is Lokesh")
# result2 = chatbot_agent.run_sync("What is my name?",message_history=result1.all_messages())

# print(result1.output)
# print("--------------------------------")
# print(result2.output)


# print(result2.all_messages_json())