
// src/lib/api.ts
import { config } from './config';

export interface Project {
  id: string;
  title: string;
  summary: string;
  tags: string[];
  links: {
    github?: string;
    live?: string;
    demo?: string;
  };
}

export interface ContactForm {
  name: string;
  email: string;
  message: string;
}

export const api = {
  async getProjects(): Promise<Project[]> {
    try {
      const response = await fetch(`${config.API_BASE_URL}/api/projects`);
      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }
      return response.json();
    } catch (error) {
      console.error('Error fetching projects:', error);
      // Fallback to stub data if backend is not available
      if (config.IS_DEV) {
        return getStubProjects();
      }
      throw error;
    }
  },

  async sendContact(form: ContactForm): Promise<void> {
    const response = await fetch(`${config.API_BASE_URL}/api/contact`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(form),
    });

    if (!response.ok) {
      throw new Error('Failed to send contact form');
    }
  },
};

// Stub data for development
function getStubProjects(): Project[] {
  return [
    {
      id: '1',
      title: 'Portfolio Website',
      summary: 'A modern portfolio website built with Next.js and TypeScript',
      tags: ['Next.js', 'TypeScript', 'Tailwind CSS'],
      links: {
        github: 'https://github.com/example/portfolio',
        live: 'https://portfolio.example.com',
      },
    },
    {
      id: '2',
      title: 'E-commerce Platform',
      summary: 'Full-stack e-commerce solution with React and Node.js',
      tags: ['React', 'Node.js', 'MongoDB', 'Stripe'],
      links: {
        github: 'https://github.com/example/ecommerce',
        demo: 'https://demo-ecommerce.example.com',
      },
    },
    {
      id: '3',
      title: 'Task Management App',
      summary: 'Collaborative task management application with real-time updates',
      tags: ['Vue.js', 'Firebase', 'Real-time'],
      links: {
        github: 'https://github.com/example/taskapp',
        live: 'https://tasks.example.com',
      },
    },
  ];
}
