import type { Metadata } from 'next';
import { api } from '@/lib/api';
import ProjectCard from '@/components/ProjectCard';

export const metadata: Metadata = {
  title: 'Projects | Portfolio',
  description: 'Explore my latest web development projects and technical work',
};

export default async function ProjectsPage() {
  let projects: any[] = [];
  let error = null;

  try {
    projects = await api.getProjects();
  } catch (err) {
    error = 'Failed to load projects';
    console.error('Error loading projects:', err);
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="text-center py-20">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Projects</h1>
          <p className="text-xl text-gray-600 mb-8">
            Showcasing my latest work and technical achievements
          </p>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
            <p className="text-red-700">{error}</p>
            <p className="text-red-600 text-sm mt-2">
              Please try again later or check your connection.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="text-center py-20">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Projects</h1>
        <p className="text-xl text-gray-600 mb-12">
          Showcasing my latest work and technical achievements
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {projects?.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>

      {projects?.length === 0 && (
        <div className="text-center py-20">
          <p className="text-gray-600 text-lg">No projects found.</p>
        </div>
      )}
    </div>
  );
}
