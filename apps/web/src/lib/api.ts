import { curatedProjects, type PortfolioProject } from "./content";

export type Project = PortfolioProject;

export interface ContactForm {
  name: string;
  email: string;
  message: string;
}

export const api = {
  async getProjects(): Promise<Project[]> {
    return curatedProjects;
  },

  async sendContact(form: ContactForm): Promise<void> {
    void form;
    throw new Error(
      "Contact submission is static-first. Use the mailto link on /contact or configure a reviewed backend adapter.",
    );
  },
};
