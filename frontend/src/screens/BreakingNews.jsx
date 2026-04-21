import { useNavigate } from 'react-router-dom';
import styles from './BreakingNews.module.css';
import useGameStore from '../store/gameSlice';
import aiCompany from '../assets/shitty_logo.png'
import advertisement1 from '../assets/Protein_separation_ad.png';
import advertisement2 from '../assets/Grow_hela.png';
import advertisement4 from '../assets/EscapeRoom.png';
import advertisement5 from '../assets/proteomics_ad.png';
import advertisement6 from '../assets/spectrometry_ad.png';


function Header() {
  const time = "2026-03-14";
  return (
    <div className={styles.header}>
      <div className={styles.rightHeader}>
        <img className={styles.logo} src={aiCompany} alt="add company logo" />
      </div>
      <div className={styles.leftHeader}>
        <h3>
          {time}
        </h3>
      </div>
    </div>
  );
}

function Title({ text }) {

  return (
    <div className={styles.title}>
      <h1 className={styles.tabloidChaosTitle} >
        {text}
      </h1>
    </div>
  )
}

function Aside({ className, ads }) {
  return (
    <div className={className}>
      {ads.map(({ adPic, adTitle, adText }, index) => (
        <div key={index} className={styles.sideAdBox}>
          <img className={styles.sideAdBoxImage} src={adPic} alt="Ad" />
          <div className={styles.sideAdContent}>
            <h3 className={styles.sideAdTitle}>{adTitle}</h3>
            <p className={styles.sideAdText}>{adText}</p>
          </div>
        </div>
      ))}
    </div>
  );
}


function AdBox({ adPic, adTitle, adText }) {
  return (
    <div className={styles.adBox}>
      <img className={styles.adBoxImage} src={adPic} alt="Add an Ad" />
      <div className={styles.adBoxBox}>
        <h3 className={styles.adBoxTitle}> {adTitle} </h3>
        <p className={styles.adBoxText}> {adText} </p>
      </div>
    </div>
  );
}

function TextBox({ text }) {
  return (
    <div className={styles.textBox}>
      <p className={styles.textBoxText}>
        {text}
      </p>
    </div>
  );
}

function NextButton() {
  const navigate = useNavigate();

  return (
    <button className={styles.nextButton} onClick={() => navigate("/world")}>
      So let's go save the world!
    </button>
  );
}

function Page() {  // all the text and main adds on the page
  const userName = useGameStore((s) => s.userName);
  const playerName = userName || '[PLAYER NAME]';

  const text1 = `
Hospitals across multiple continents are reporting cases of a rapidly progressing neurological and metabolic disorder. Patients initially present with fatigue and mild fever… but within 48 hours, symptoms escalate to severe cellular degradation.

Doctors are calling it Proteome Collapse Syndrome (PCS).

Standard genetic sequencing has failed to identify the cause. Early reports suggest abnormal protein expression and misfolding at unprecedented levels.

`;
  const text2 = `

The World Health Organization is urging all proteomics laboratories to assist in identifying the molecular mechanisms behind this outbreak.

Time is critical.

Dr. ${playerName}, you have been granted emergency access to a high-priority dataset recovered from infected patients.

Your mission:
Identify the proteins and pathways driving this disease… and help develop a cure before it spreads beyond control.
`;
  const adPic4 = advertisement4
  const adTitle4 = "Escape room for the advanced protein scientists!"
  const adText4 = "Being a protein scientist also needs its fun parts. BUY this amazing escape room game and relax! Solve puzzles and escape the lab before time runs out!";

  return (
    <div className={styles.page}>
      <TextBox text={text1} ></TextBox>
      <TextBox text={text2} ></TextBox>
      <div className={styles.center} style={{ marginBottom: '20px' }}>
        <NextButton></NextButton>
      </div>
      <AdBox adPic={adPic4} adTitle={adTitle4} adText={adText4} ></AdBox>
    </div>
  )
}


function Canvas() {    // the title box plus the Page
  const titleText = "📺 GLOBAL EMERGENCY BROADCAST 📺"
  return (
    <div className={styles.canvas}>
      <Title text={titleText}></Title>
      <Page ></Page>
    </div>
  );
}


export default function News() {
  const adPic1 = advertisement5
  const adTitle1 = "RESEARCHER DON'T WANT YOU TO KNOW"
  const adText1 = "Who needs school, when you can, with the click of a button, perform the most advanced research in the world."
  const adPic2 = advertisement6
  const adTitle2 = "GET IT NOW OR MISS THE OPPORTUNITY!!!"
  const adText2 = "The super instrument of this century! So sensitive that it makes you cry tears of joy each time"
  const adPic3 = advertisement2
  const adTitle3 = 'GROW GROW GROWWW'
  const adText3 = 'A day cannot go by without thinking of buying this super product! -Dr. smith'
  const adPic4 = advertisement1
  const adTitle4 = 'Separates faster than ever!'
  const adText4 = 'The ultimate protein separator that puts scientists out of work.';

  const leftSideAds = [
    { adPic: adPic1, adTitle: adTitle1, adText: adText1 },
    { adPic: adPic3, adTitle: adTitle3, adText: adText3 },
  ];
  const rightSideAds = [
    { adPic: adPic2, adTitle: adTitle2, adText: adText2 },
    { adPic: adPic4, adTitle: adTitle4, adText: adText4 },
  ];

  return (
    <div className={styles.layout}>
      <Header ></Header>
      <Aside className={`${styles.aside} ${styles.leftAside}`} ads={leftSideAds}></Aside>
      <Canvas ></Canvas>
      <Aside className={`${styles.aside} ${styles.rightAside}`} ads={rightSideAds}></Aside>
    </div>
  );
}
