import openai
from typing import Optional, Dict, Any
import random
import logging
from core.config import settings

logger = logging.getLogger(__name__)

class AIContentGenerator:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
            logger.warning("OpenAI API key not provided. AI features disabled.")
    
    async def analyze_relevance(self, content: str, context: str, threshold: float = 0.7) -> Dict[str, Any]:
        """Analyze if content is relevant for engagement (ReplyDaddy style)"""
        
        if not self.enabled:
            return {
                'relevance_score': 0.5,
                'is_relevant': True,
                'confidence': 'disabled'
            }
        
        prompt = f"""
        Analyze this message for marketing relevance.
        
        Context: {context}
        Message: {content}
        
        Score from 0.0 to 1.0 how relevant this message is for someone in {context} business.
        Consider:
        - Does the user seem to need solutions in this area?
        - Are they asking for recommendations?
        - Do they express pain points we could address?
        - Is this a good opportunity for helpful engagement?
        
        Respond with just a number between 0.0 and 1.0.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.3
            )
            
            score_text = response.choices.message.content.strip()
            score = float(score_text)
            
            return {
                'relevance_score': score,
                'is_relevant': score >= threshold,
                'confidence': 'high' if score >= 0.8 else 'medium' if score >= 0.5 else 'low'
            }
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return {
                'relevance_score': 0.0,
                'is_relevant': False,
                'confidence': 'error',
                'error': str(e)
            }
    
    async def generate_response(self, 
                              original_content: str, 
                              user_profile: Dict[str, str],
                              brand_context: str) -> str:
        """Generate human-like response (ReplyDaddy style)"""
        
        if not self.enabled:
            return self._generate_fallback_response(original_content, user_profile.get('brand_name', 'our platform'))
        
        tone = user_profile.get('tone', 'helpful and casual')
        industry = user_profile.get('industry', 'technology')
        brand_name = user_profile.get('brand_name', 'our platform')
        
        prompt = f"""
        Generate a natural, helpful response to this message:
        "{original_content}"
        
        Guidelines:
        - Tone: {tone}
        - Industry context: {industry}
        - Be genuinely helpful first
        - Keep it under 200 characters
        - Sound human with natural language
        - Add 1-2 minor typos or casual abbreviations for authenticity
        - Never mention direct links
        - If relevant, subtly mention "{brand_name}" as a solution
        - Match the conversation style
        
        Brand context: {brand_context}
        
        Generate just the response message, nothing else.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.8  # Higher creativity for natural responses
            )
            
            generated_response = response.choices.message.content.strip()
            
            # Add human-like variations
            generated_response = self._add_human_touches(generated_response)
            
            return generated_response
            
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            # Fallback to template response
            return self._generate_fallback_response(original_content, brand_name)
    
    def _add_human_touches(self, text: str) -> str:
        """Add subtle human-like imperfections"""
        
        # Random minor typos (very sparingly)
        typo_chance = random.random()
        if typo_chance < 0.1:  # 10% chance
            typos = {
                'you': 'u',
                'your': 'ur',
                'are': 'r',
                'because': 'bc',
                'probably': 'prob',
                'definitely': 'def'
            }
            for original, typo in typos.items():
                if original in text.lower():
                    text = text.replace(original, typo, 1)
                    break
        
        # Add casual punctuation
        if not text.endswith(('.', '!', '?')):
            endings = ['.', '!', ' :)', ' 👍']
            text += random.choice(endings)
        
        return text
    
    def _generate_fallback_response(self, original_content: str, brand_name: str) -> str:
        """Generate fallback response when AI fails"""
        templates = [
            "That's a great point! Have you considered looking into {brand_name}?",
            "I had the same issue! {brand_name} actually helped me solve this.",
            "Interesting question! You might want to check out {brand_name} for this.",
            "I've seen good results with {brand_name} for similar situations."
        ]
        
        return random.choice(templates).format(brand_name=brand_name)

# Global AI service instance
ai_service = AIContentGenerator()