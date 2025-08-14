import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'About | Portfolio',
  description: 'Learn more about my background, skills, and experience in web development',
};

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-12">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">About Me</h1>
        <p className="text-xl text-gray-600">
          Passionate developer with a love for clean code and user experience
        </p>
      </div>

      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Background</h2>
        <p className="text-gray-700 leading-relaxed">
          I'm a full-stack developer with over 5 years of experience building web applications. 
          I specialize in modern JavaScript frameworks, Python backend development, and cloud infrastructure.
        </p>
        <p className="text-gray-700 leading-relaxed">
          My journey in tech started with curiosity and has evolved into a passion for creating 
          solutions that make a difference. I believe in writing maintainable code, following best practices, 
          and continuously learning new technologies.
        </p>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Experience</h2>
        <div className="space-y-4">
          <div className="border-l-4 border-blue-600 pl-4">
            <h3 className="font-semibold text-gray-900">Senior Full-Stack Developer</h3>
            <p className="text-gray-600">Tech Company • 2022 - Present</p>
            <p className="text-gray-700 mt-2">
              Lead development of enterprise web applications using React, Node.js, and Python. 
              Mentored junior developers and implemented CI/CD pipelines.
            </p>
          </div>
          
          <div className="border-l-4 border-blue-600 pl-4">
            <h3 className="font-semibold text-gray-900">Web Developer</h3>
            <p className="text-gray-600">Digital Agency • 2020 - 2022</p>
            <p className="text-gray-700 mt-2">
              Built responsive websites and e-commerce platforms for various clients. 
              Worked with WordPress, custom PHP, and modern frontend frameworks.
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Education</h2>
        <div className="border-l-4 border-blue-600 pl-4">
          <h3 className="font-semibold text-gray-900">Bachelor of Computer Science</h3>
          <p className="text-gray-600">University Name • 2016 - 2020</p>
          <p className="text-gray-700 mt-2">
            Focused on software engineering, algorithms, and web technologies. 
            Graduated with honors and completed several relevant projects.
          </p>
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">What I Do</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="font-semibold text-gray-900 mb-3">Frontend Development</h3>
            <p className="text-gray-700">
              Building responsive, accessible user interfaces with React, TypeScript, and modern CSS.
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="font-semibold text-gray-900 mb-3">Backend Development</h3>
            <p className="text-gray-700">
              Creating robust APIs and server-side logic with Python, Node.js, and various databases.
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="font-semibold text-gray-900 mb-3">DevOps & Deployment</h3>
            <p className="text-gray-700">
              Setting up CI/CD pipelines, containerization with Docker, and cloud deployment.
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="font-semibold text-gray-900 mb-3">Problem Solving</h3>
            <p className="text-gray-700">
              Analyzing complex requirements and designing efficient, scalable solutions.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
