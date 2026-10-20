from claude_agent_sdk import ClaudeAgentOptions, Message, AssistantMessage, SystemMessage, ResultMessage, TextBlock, ToolUseBlock, ToolResultBlock

MODEL_NAME = 'claude-haiku-4-5'


def reusable_options(**args)->ClaudeAgentOptions:
    settings = {
        'model' : MODEL_NAME,
        'max_turns' : 3
    }

    settings.update(args)

    options = ClaudeAgentOptions(**settings)
    return options

def parse_message(message : Message):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(f'response from llm ={block.text}')
            if isinstance(block, ToolUseBlock):
                print(f'{block.name}')
                print(f'{block.input}')
            if isinstance(block,ToolResultBlock):
                print(f'{block.content}')
    elif isinstance(message, ResultMessage):
        print(f'total cost in USD = {message.total_cost_usd}')
        print(f'session id = {message.session_id}')
        return message.session_id
    elif isinstance(message,SystemMessage):
        print(f'{message.data}')
