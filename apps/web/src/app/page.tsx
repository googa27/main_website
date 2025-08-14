import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="text-center py-20">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">
          Hi, I'm <span className="text-blue-600">Your Name</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          A passionate full-stack developer specializing in modern web technologies. 
          I build scalable, user-friendly applications that solve real-world problems.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/projects"
            className="bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            View My Work
          </Link>
          <Link
            href="/contact"
            className="border border-blue-600 text-blue-600 px-8 py-3 rounded-lg font-medium hover:bg-blue-50 transition-colors"
          >
            Get In Touch
          </Link>
        </div>
      </section>

      {/* Skills Section */}
      <section className="py-16">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
          Technologies I Work With
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
          {[
            { name: 'React', icon: '⚛️' },
            { name: 'TypeScript', icon: '📘' },
            { name: 'Node.js', icon: '🟢' },
            { name: 'Python', icon: '🐍' },
            { name: 'Next.js', icon: '▲' },
            { name: 'PostgreSQL', icon: '🐘' },
            { name: 'Docker', icon: '🐳' },
            { name: 'AWS', icon: '☁️' },
          ].map((skill) => (
            <div key={skill.name} className="text-center">
              <div className="text-4xl mb-2">{skill.icon}</div>
              <div className="text-gray-700 font-medium">{skill.name}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="text-center py-16 bg-blue-50 rounded-lg">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          Ready to Build Something Amazing?
        </h2>
        <p className="text-gray-600 mb-8 max-w-2xl mx-auto">
          Let's discuss your project and see how we can work together to bring your ideas to life.
        </p>
        <Link
          href="/contact"
          className="bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          Start a Conversation
        </Link>
      </section>
    </div>
  );
}
