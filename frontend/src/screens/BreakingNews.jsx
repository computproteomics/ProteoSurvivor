import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './BreakingNews.module.css';
import aiCompany from '../assets/shitty_logo.png'
import advertisement1 from '../assets/Protein_separation_ad.png';
import advertisement2 from '../assets/Grow_hela.png';
import advertisement3 from '../assets/Omnispec.png';
import advertisement4 from '../assets/EscapeRoom.png';
import advertisement5 from '../assets/proteomics_ad.png';
import advertisement6 from '../assets/spectrometry_ad.png';


function Header({  }) {
  const company_logo = aiCompany;
  const time = "2003-09-11";
  return(
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

  return(
    <div className={styles.title}>
      <h1 className={styles.tabloidChaosTitle} >
        {text}
      </h1>
    </div>
  )
}

function Aside( {className, adPic, adText, adTitle }) {
  return(
    <div className={className}>
      <img className={styles.adImage} src={adPic} alt="Add"></img>
      <h3 className={styles.adTitle}>{adTitle}</h3>
      <p className={styles.adText}>{adText}</p>

    </div>
  );
}


function AdBox({ adPic, adTitle, adText }) {
  return(
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
  return(
    <div className={styles.textBox}>
      <p className={styles.textBoxText}>
        {text}
      </p>
    </div>
  );
}

function NextButton() {
  const navigate = useNavigate();

  return(
    <button onClick={() => navigate("/world")}>
      Go To world
    </button>
  );
}

function Page() {  // all the text and main adds on the page
  const text1 = "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.m"
  const text2 = "It is a long established fact that a reader will be distracted by the readable content of a page when looking at its layout. The point of using Lorem Ipsum is that it has a more-or-less normal distribution of letters, as opposed to using 'Content here, content here', making it look like readable English. Many desktop publishing packages and web page editors now use Lorem Ipsum as their default model text, and a search for 'lorem ipsum' will uncover many web sites still in their infancy. Various versions have evolved over the years, sometimes by accident, sometimes on purpose (injected humour and the like)."
  const text3 = " Contrary to popular belief, Lorem Ipsum is not simply random text. It has roots in a piece of classical Latin literature from 45 BC, making it over 2000 years old. Richard McClintock, a Latin professor at Hampden-Sydney College in Virginia, looked up one of the more obscure Latin words, consectetur, from a Lorem Ipsum passage, and going through the cites of the word in classical literature, discovered the undoubtable source. Lorem Ipsum comes from sections 1.10.32 and 1.10.33 of \"de Finibus Bonorum et Malorum\" (The Extremes of Good and Evil) by Cicero, written in 45 BC. This book is a treatise on the theory of ethics, very popular during the Renaissance. The first line of Lorem Ipsum, \"Lorem ipsum dolor sit amet..\", comes from a line in section 1.10.32."
  const text4 = "There are many variations of passages of Lorem Ipsum available, but the majority have suffered alteration in some form, by injected humour, or randomised words which don't look even slightly believable. If you are going to use a passage of Lorem Ipsum, you need to be sure there isn't anything embarrassing hidden in the middle of text. All the Lorem Ipsum generators on the Internet tend to repeat predefined chunks as necessary, making this the first true generator on the Internet. It uses a dictionary of over 200 Latin words, combined with a handful of model sentence structures, to generate Lorem Ipsum which looks reasonable. The generated Lorem Ipsum is therefore always free from repetition, injected humour, or non-characteristic words etc."
  const adPic1 = advertisement1 
  const adTitle1 = "THE ULTIMATE PROTEIN SEPARATOR THAT PUTS SCIENTISTS OUT OF WORK"
  const adText1 = ""
  const adPic2 = advertisement2
  const adTitle2 = "Title placeholder2"
  const adText2 = "Minor placeholder"
  const adPic3 = advertisement3
  const adTitle3 = "Title placeholder3"
  const adText3 = "Minor placeholder"
  const adPic4 = advertisement4
  const adTitle4 = "Title placeholder4"
  const adText4 = "Minor placeholder"
  
  return(
    <div className={styles.page}>
      <TextBox text={text1} ></TextBox>
      <AdBox adPic={adPic1} adTitle={adTitle1} adText={adText1} ></AdBox>
      <TextBox text={text2} ></TextBox>
      <AdBox adPic={adPic2} adTitle={adTitle2} adText={adText2} ></AdBox>
      <TextBox text={text3} ></TextBox>
      <AdBox adPic={adPic3} adTitle={adTitle3} adText={adText3} ></AdBox>
      <TextBox text={text4} ></TextBox>
      <AdBox adPic={adPic4} adTitle={adTitle4} adText={adText4} ></AdBox>
    </div>
  )
}


function Canvas() {    // the title box plus the Page
  const titleText = "THIS IS A TITLE"
  return(
    <div className={styles.canvas}>
      <Title text={titleText}></Title>
      <Page ></Page>
    </div>
  );
}


export default function News() {
  const adPic1 = advertisement5
  const adTitle1 = "RESEARCHERS DON'T WANT YOU TO KNOW"
  const adText1 = "THe best proteomics software in the world. Who needs school, when you can, with the click of a button, perform the most advanced research in the world."
  const adPic2 = advertisement6
  const adTitle2 = "PLACEHOLDER 2"
  const adText2 = "This is placeholder for ad text 2"


  return(
    <div className={styles.layout}>
      <Header ></Header>
      <Aside className={`${styles.aside} ${styles.leftAside}`} adPic={adPic1} adText={adText1} adTitle={adTitle1}></Aside>
      <Canvas ></Canvas>
      <Aside className={`${styles.aside} ${styles.rightAside}`} adPic={adPic2} adText={adText2} adTitle={adTitle2}></Aside>
      <NextButton></NextButton>
    </div>
  );
}
