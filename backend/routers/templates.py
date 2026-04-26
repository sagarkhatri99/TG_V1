from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import traceback

from database import get_db
from models import MessageTemplate, User
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/templates",
    tags=["Templates"]
)

class TemplateCreate(BaseModel):
    name: str
    content: str
    category: Optional[str] = "general"

class TemplateResponse(BaseModel):
    id: int
    name: str
    content: str
    category: Optional[str]
    spam_risk_score: float
    variables: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

_TEMPLATES_TABLE_VERIFIED = False

@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all templates for current user"""
    global _TEMPLATES_TABLE_VERIFIED
    
    logger.info(f"[TEMPLATES] GET /api/templates - user_id={current_user.id} email={current_user.email}")
    try:
        # Verify table exists only once per process startup
        if not _TEMPLATES_TABLE_VERIFIED:
            result = db.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='message_templates'")).scalar()
            if result == 0:
                logger.error("[TEMPLATES] message_templates table MISSING")
                raise HTTPException(status_code=500, detail="Database table missing")
            _TEMPLATES_TABLE_VERIFIED = True
            logger.info("[TEMPLATES] message_templates table verified")

        templates = db.query(MessageTemplate).filter(
            MessageTemplate.user_id == current_user.id
        ).order_by(MessageTemplate.created_at.desc()).all()
        logger.info(f"[TEMPLATES] Found {len(templates)} templates for user_id={current_user.id}")
        return templates
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEMPLATES] ERROR listing templates: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new message template"""
    logger.info(f"[TEMPLATES] POST /api/templates - user_id={current_user.id} name='{template_data.name}'")
    
    # Extract variables from content (find all {word|word2|word3} patterns)
    import re
    variables = []
    pattern = r'\{([^}]+)\}'
    matches = re.findall(pattern, template_data.content)
    for match in matches:
        # Split by | to get all variants
        variants = [v.strip() for v in match.split('|')]
        variables.extend(variants)
    
    # Remove duplicates
    variables = list(set(variables))
    
    # Calculate spam risk (basic heuristic)
    spam_keywords = ['free', 'win', 'click here', 'limited time', 'act now', 'guaranteed']
    spam_score = sum(5.0 for keyword in spam_keywords if keyword.lower() in template_data.content.lower())
    spam_score = min(spam_score, 100.0)  # Cap at 100
    
    # Create template
    new_template = MessageTemplate(
        user_id=current_user.id,
        name=template_data.name,
        content=template_data.content,
        category=template_data.category,
        spam_risk_score=spam_score,
        variables=variables,
        created_at=datetime.utcnow()
    )
    
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return new_template

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific template"""
    template = db.query(MessageTemplate).filter(
        MessageTemplate.id == template_id,
        MessageTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template

@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a template"""
    template = db.query(MessageTemplate).filter(
        MessageTemplate.id == template_id,
        MessageTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template deleted successfully"}

@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template_data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a template"""
    template = db.query(MessageTemplate).filter(
        MessageTemplate.id == template_id,
        MessageTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Extract variables
    import re
    variables = []
    pattern = r'\{([^}]+)\}'
    matches = re.findall(pattern, template_data.content)
    for match in matches:
        variants = [v.strip() for v in match.split('|')]
        variables.extend(variants)
    variables = list(set(variables))
    
    # Update fields
    template.name = template_data.name
    template.content = template_data.content
    template.category = template_data.category
    template.variables = variables
    template.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(template)
    
    return template

@router.get("/{template_id}/preview")
async def preview_template(
    template_id: int,
    count: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate sample messages from a template using spintax"""
    import re
    import random
    
    template = db.query(MessageTemplate).filter(
        MessageTemplate.id == template_id,
        MessageTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    def generate_message(content: str) -> str:
        """Generate a single message by randomly selecting from spintax options"""
        # Pattern to match {option1|option2|option3}
        pattern = r'\{([^}]+)\}'
        
        def replace_spintax(match):
            options = match.group(1).split('|')
            return random.choice([opt.strip() for opt in options])
        
        return re.sub(pattern, replace_spintax, content)
    
    # Generate requested number of sample messages
    samples = [generate_message(template.content) for _ in range(min(count, 10))]
    
    return {
        "template_id": template_id,
        "template_name": template.name,
        "samples": samples
    }
