import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock ollama before importing ai_client
sys.modules['ollama'] = MagicMock()
from ai_client import AIClient

class TestAIClient(unittest.TestCase):
    @patch('ai_client.ollama')
    def test_memory(self, mock_ollama):
        # Setup mock to return a simple response
        mock_ollama.chat.return_value = {'message': {'content': 'I am the AI.'}}
        
        client = AIClient()
        
        # message 1
        client.chat("Hello")
        
        # Check history length
        # History should be: user msg, ai msg
        self.assertEqual(len(client.history), 2)
        self.assertEqual(client.history[0]['role'], 'user')
        self.assertEqual(client.history[0]['content'], 'Hello')
        self.assertEqual(client.history[1]['role'], 'assistant')
        
        # message 2
        client.chat("How are you?")
        
        # History should be: user, ai, user, ai
        self.assertEqual(len(client.history), 4)
        
        # Verify call to ollama included full history
        # The last call to chat should have passed the history of length 3 (before the 2nd AI response)
        # But wait, we append user msg BEFORE calling chat.
        # So for the 2nd call: history has [u1, a1, u2]
        # mock_ollama.chat should be called with this list.
        
        # Get the arguments of the last call
        call_args = mock_ollama.chat.call_args
        passed_messages = call_args.kwargs['messages']
        self.assertEqual(len(passed_messages), 3)
        self.assertEqual(passed_messages[2]['content'], 'How are you?')

    @patch('ai_client.ollama')
    def test_memory_limit(self, mock_ollama):
        mock_ollama.chat.return_value = {'message': {'content': 'Ack'}}
        client = AIClient()
        client.history_limit = 4 # very small limit for testing
        
        # Chat 3 times (6 messages total would be generated)
        client.chat("1") # history: u1, a1 (2)
        client.chat("2") # history: u1, a1, u2, a2 (4)
        client.chat("3") # history: u1, a1, u2, a2, u3 .. pruned to 4 .. -> u2, a2, u3, a3 (4)
        
        self.assertEqual(len(client.history), 5)
        self.assertEqual(client.history[-1]['content'], 'Ack')
        # The oldest message "1" should be gone.
        self.assertNotIn("1", [m['content'] for m in client.history])

if __name__ == '__main__':
    unittest.main()
