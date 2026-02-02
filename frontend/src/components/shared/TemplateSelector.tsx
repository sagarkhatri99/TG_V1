import React, { useEffect, useState } from 'react';
import { FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import api from '../../api/Index';
import type { Template } from '../../Types/Index';

interface TemplateSelectorProps {
  value?: number | null;
  onChange: (template: Template | null) => void;
  category?: string;
}

export const TemplateSelector: React.FC<TemplateSelectorProps> = ({
  value,
  onChange,
  category
}) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, [category]);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/campaigns/templates', {
        params: category ? { category } : {}
      });
      setTemplates(response.data);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (event: SelectChangeEvent<number>) => {
    const templateId = event.target.value as number;
    const template = templates.find(t => t.id === templateId);
    onChange(template || null);
  };

  return (
    <FormControl fullWidth>
      <InputLabel id="template-selector-label">Select Template</InputLabel>
      <Select
        labelId="template-selector-label"
        value={value || ''}
        label="Select Template"
        onChange={handleChange}
        disabled={loading}
      >
        <MenuItem value="">
          <em>-- No Template --</em>
        </MenuItem>
        {templates.map(template => (
          <MenuItem key={template.id} value={template.id}>
            {template.name} {template.category && `(${template.category})`}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};
