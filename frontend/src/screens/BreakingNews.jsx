import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './BreakingNews.module.css';


function Header({ children }) {
  const company = "TEMP"
  const time = "2003-09-11"
  return(
    <div className={styles.header}>
      <div className={styles.rightHeader}>
        <h1>
          {company}
        </h1>
      </div>
      <div className={styles.leftHeader}>
        <h1> 
          {time}
        </h1>
      </div>
    </div>
  );
}

function Title({ text }) {

  return(
    <div >
      <h1 className={styles.tabloidChaosTitle} >
        {text}
      </h1>
    </div>
  )
}

function Aside( {className, children }) {
  return(
    <div className={className}>
      {children}
    </div>
  );
}

function GetImageURL(advertisement) {

}

function MainAdd(advertisement) {
  return 
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
  
}

function Page() {  // all the text and main adds on the page
  const text1 = "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.m"
  const text2 = "Text for Box 2"
  const text3 = "Text for Box 2"
  const text4 = "Text for Box 2"
  
  return(
    <div className={styles.page}>
      <TextBox text={text1}></TextBox>
      <TextBox text={text2}></TextBox>
      <TextBox text={text3}></TextBox>
  <TextBox text={text4}></TextBox>
    </div>
  )
}


function Canvas() {    // the header plus the Page
  const titleText = "THIS IS A TITLE"
  return(
    <div className={styles.canvas}>
      <Title text={titleText}></Title>
      <Page ></Page>
    </div>
  );
}


export default function News() {
  return(
    <div className={styles.layout}>
      <Header ></Header>
      <Aside className={`${styles.aside} ${styles.leftAside}`}> Left Sidebar </Aside>
      <Canvas ></Canvas>
      <Aside className={`${styles.aside} ${styles.rightAside}`}> Right Sidebar </Aside>
    </div>
  )
}
