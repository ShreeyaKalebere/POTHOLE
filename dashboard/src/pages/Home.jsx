import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  IconArrowRight, IconBrain, IconCamera, IconClipboardCheck, IconFileText, IconListCheck, IconMapPin,
  IconPhotoSearch, IconRoute, IconShieldCheck, IconTool, IconUser, IconUserCheck, IconUserShield, IconVideo,
} from "@tabler/icons-react";
import logoUrl from "../assets/margdrishti_logo.svg";
import dashboardShot from "../assets/home-dashboard.jpg";

const STEPS = [
  [IconCamera, "Capture", "A citizen uploads a photo, or a patrol phone records the road live."],
  [IconPhotoSearch, "Detect", "YOLO11 finds potholes and alligator cracks and draws a box around each one."],
  [IconMapPin, "Locate and rate", "The system records GPS and time, estimates severity, and finds the ward."],
  [IconListCheck, "Assign", "The ward officer checks the damage and assigns a repair team."],
  [IconTool, "Repair", "The team goes to the site and uploads an “after” photo of the repair."],
  [IconClipboardCheck, "Approve", "The officer compares before and after, then approves or rejects the repair."],
];

const FEATURES = [
  [IconVideo, "Live patrol", "A phone camera on a moving vehicle tracks each defect across frames and saves it once."],
  [IconCamera, "Citizen reporting", "Anyone can report damage without an account and follow it with a tracking number."],
  [IconRoute, "Interactive road map", "Every defect appears on a map of Kolhapur, colored by severity."],
  [IconListCheck, "Priority worklist", "Open and severe damage with the most reports comes first."],
  [IconClipboardCheck, "Repair approval", "Before and after photos, with an AI check to help the officer decide."],
  [IconFileText, "Municipal reports", "Filtered PDF and CSV reports for maintenance planning."],
  [IconShieldCheck, "Role-based access", "Each person sees only their ward or jobs, and actions are logged by name."],
  [IconBrain, "Duplicate merging", "Repeat reports within 15 meters join the same open incident."],
];

const STACK = [
  ["AI and vision", "YOLO11, PyTorch, OpenCV, ByteTrack"],
  ["Backend", "Python, FastAPI"],
  ["Database", "MongoDB"],
  ["Frontend", "React.js, Leaflet, OpenStreetMap"],
];

const TEAM = ["Shreeya Kalebere", "Shubham Pattewar", "Anuj Powar", "Virendra Katale", "Preeti Sonule"];

const PANELS = [
  ["peach", IconUser, "Citizen", "Report road damage and track your report. No account needed.", "/report", "Report damage"],
  ["sky", IconTool, "Repair team", "See assigned jobs, get directions, and submit repair photos.", "/login?role=repair_team", "Repair team login"],
  ["mint", IconUserCheck, "Ward officer", "Manage your ward, assign teams, and approve repairs.", "/login?role=ward_officer", "Ward officer login"],
  ["lav", IconUserShield, "Admin", "See all wards, manage accounts, and review activity.", "/login?role=admin", "Admin login"],
];

export default function Home({ user }) {
  const { hash } = useLocation();

  // A link like /#login arrives before this page exists, so the browser cannot scroll to it alone
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
  }, [hash]);

  return (
    <div className="home">
      <header className="home-nav">
        <a className="home-brand" href="#top">
          <img className="logo" src={logoUrl} alt="MargDrishti logo" />
          <b>MargDrishti</b>
        </a>
        <nav className="home-links" aria-label="Page sections">
          <a href="#about">About</a>
          <a href="#how">How it works</a>
          <a href="#features">Features</a>
          <a href="#model">AI model</a>
          <a href="#team">Team</a>
        </nav>
        {user ? <Link className="btn primary" to="/">Open my panel</Link> : <a className="btn primary" href="#login">Login</a>}
      </header>

      <main id="top">
        <section className="home-hero">
          <div>
            <p className="eyebrow">Marg (road) + Drishti (vision)</p>
            <h1>AI that finds road damage and follows it until it is repaired</h1>
            <p className="hero-text">
              MargDrishti detects potholes and alligator cracks from photos and live video, records where they are,
              and gives municipal teams one place to plan, assign, and verify repairs in Kolhapur.
            </p>
            <div className="hero-actions">
              <Link className="btn primary big-link" to="/report">Report road damage<IconArrowRight size={18} aria-hidden="true" /></Link>
              <a className="btn big-link" href="#login">Choose your panel</a>
            </div>
          </div>
          <figure className="hero-shot">
            <img src={dashboardShot} alt="MargDrishti dashboard with damage counts, a map of Kolhapur, a repair list and charts" />
            <figcaption>The officer dashboard. Many records shown here are demo data.</figcaption>
          </figure>
        </section>

        <section id="about" className="home-section about">
          <div>
            <h2>The problem</h2>
            <p>Road inspections are usually manual and slow. Damage can be recorded inconsistently, reports get scattered, and it is hard to tell which roads to fix first or whether a repair was really finished.</p>
          </div>
          <div>
            <h2>Our solution</h2>
            <p>MargDrishti links detection to action. Each defect gets a location, severity, ward, and history, then moves through a clear path from report to approved repair.</p>
          </div>
        </section>

        <section id="how" className="home-section">
          <h2>How it works</h2>
          <ol className="flow">
            {STEPS.map(([Icon, title, text], k) => (
              <li key={title}>
                <span className="flow-num">{k + 1}</span>
                <Icon size={26} stroke={1.7} aria-hidden="true" />
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="features" className="home-section">
          <h2>What the system does</h2>
          <div className="feature-grid">
            {FEATURES.map(([Icon, title, text]) => (
              <article key={title}>
                <Icon size={24} stroke={1.7} aria-hidden="true" />
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="model" className="home-section">
          <h2>The AI model</h2>
          <p className="section-intro">The app runs YOLO11s at 640 px and detects two classes: pothole and alligator crack. These are measured results on images the model did not train on.</p>
          <div className="metric-grid">
            <div className="metric peach"><b>75.2%</b><span>mAP@50</span></div>
            <div className="metric lemon"><b>85.1%</b><span>Precision</span></div>
            <div className="metric mint"><b>65.5%</b><span>Recall</span></div>
            <div className="metric sky"><b>~15 ms</b><span>Per image on an RTX 4060</span></div>
          </div>
        </section>

        <section id="login" className="home-section login-section">
          <h2>Choose your panel</h2>
          <p className="section-intro">Citizens can start right away. Staff log in with the account given by the admin.</p>
          <div className="panel-grid">
            {PANELS.map(([tone, Icon, title, text, to, cta]) => (
              <Link key={title} className={`panel-card ${tone}`} to={to}>
                <Icon size={30} stroke={1.7} aria-hidden="true" />
                <h3>{title}</h3>
                <p>{text}</p>
                <span className="panel-cta">{cta}<IconArrowRight size={17} aria-hidden="true" /></span>
              </Link>
            ))}
          </div>
        </section>

        <section className="home-section stack-team">
          <div>
            <h2>Technology</h2>
            <dl className="stack">
              {STACK.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
            </dl>
          </div>
          <div id="team">
            <h2>Team</h2>
            <p className="muted">Group G3, DYPCET Kolhapur</p>
            <ul className="team">
              {TEAM.map((n) => <li key={n}>{n}</li>)}
            </ul>
            <p><b>Guide:</b> Mrs. S. V. Shinge</p>
          </div>
        </section>
      </main>

      <footer className="home-foot">
        <p>MargDrishti is a final-year project and is not an official service of the Kolhapur Municipal Corporation.</p>
        <p>Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors.</p>
      </footer>
    </div>
  );
}
