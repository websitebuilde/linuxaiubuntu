import ollama

class AIClient:
    def __init__(self, model="llama3"):
        self.model = model
        self.history = []
        self.history_limit = 20

    def chat(self, user_input):
        """
        General chat with the AI.
        """
        try:
            # Add user message to history
            self.history.append({'role': 'user', 'content': user_input})
            
            # Prune history if needed (keep system prompt if we had one, but here we just keep last N)
            if len(self.history) > self.history_limit:
                 self.history = self.history[-self.history_limit:]

            response = ollama.chat(model=self.model, messages=list(self.history))
            reply = response['message']['content']
            
            # Add assistant response to history
            self.history.append({'role': 'assistant', 'content': reply})
            
            return reply
        except Exception as e:
            return f"Error connecting to AI: {e}"

    def generate_command(self, user_intent):
        """
        Ask AI to translate natural language to a terminal command.
        """
        prompt = f"""
        You are an Ubuntu command line expert. 
        Translate the following user request into a single valid bash command. 
        Do not explain. Do not use markdown code blocks. Just output the command.
        
        User Request: {user_intent}
        Command:
        """
        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            return response['response'].strip()
        except Exception as e:
            return f"Error generating command: {e}"
