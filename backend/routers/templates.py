from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import MessageTemplate, User
from routers.auth import get_current_user

router = APIRouter(
    prefix="/api/campaigns/templates",
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

@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all templates for current user"""
    templates = db.query(MessageTemplate).filter(
        MessageTemplate.user_id == current_user.id
    ).order_by(MessageTemplate.created_at.desc()).all()
    return templates

@router.post("/", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new message template"""
    
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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
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
