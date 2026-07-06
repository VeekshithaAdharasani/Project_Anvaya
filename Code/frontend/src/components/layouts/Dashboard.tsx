// import React from 'react';
// import { Header } from './Header';

// interface DashboardProps {
//   graphViewElement: React.ReactNode;
//   chatPanelElement: React.ReactNode;
//   chapterDetailsElement: React.ReactNode;
//   discoveryCardElement: React.ReactNode;
//   questionsCardElement: React.ReactNode; // Slot added
//   statusElement?: React.ReactNode;
//   storyOfUnderstandingElement: React.ReactNode;
// }

// export const Dashboard: React.FC<DashboardProps> = ({
//   graphViewElement,
//   chatPanelElement,
//   chapterDetailsElement,
//   discoveryCardElement,
//   questionsCardElement,
//   storyOfUnderstandingElement,
//   statusElement,
// }) => {
//   return (
//     <div className="anvaya-wrapper">
//       <Header />

//       {statusElement && (
//         <div className="status-area">
//           {statusElement}
//         </div>
//       )}

//       <main className="dashboard-workspace">
//         <section className="panel-container">
//           <div className="panel-title">
//             <span className="panel-icon-wrapper">
//               <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
//                 <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
//                 <path d="M12 6v12M6 12h12"/>
//               </svg>
//             </span>
//             Map of Understanding
//           </div>
//           {graphViewElement}
//         </section>

//         <section className="panel-container">
//           <div className="panel-title">
//             <span className="panel-icon-wrapper">
//               <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
//                 <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
//               </svg>
//             </span>
//             Conversation
//           </div>
//           {chatPanelElement}
//         </section>
//       </main>

//       <section className="bottom-cards-grid">
//         {discoveryCardElement}
//         {questionsCardElement}
//         {chapterDetailsElement}
//       </section>
//       <section className="story-section">
//         {storyOfUnderstandingElement}
//       </section>
//     </div>
//   );
// };


import React from 'react';
import { Header } from './Header';

interface DashboardProps {
  graphViewElement: React.ReactNode;
  chatPanelElement: React.ReactNode;
  chapterDetailsElement: React.ReactNode;
  discoveryCardElement: React.ReactNode;
  questionsCardElement: React.ReactNode; // Slot added
  statusElement?: React.ReactNode;
  storyOfUnderstandingElement: React.ReactNode;
}

export const Dashboard: React.FC<DashboardProps> = ({
  graphViewElement,
  chatPanelElement,
  chapterDetailsElement,
  discoveryCardElement,
  questionsCardElement,
  storyOfUnderstandingElement,
  statusElement,
}) => {
  return (
    <div className="anvaya-wrapper">
      <Header />

      {statusElement && (
        <div className="status-area">
          {statusElement}
        </div>
      )}

      <main className="dashboard-workspace">
        {/* Left Workspace: Conversation (60% - The Active Journal Page) */}
        <section className="panel-container conversation-panel-container">
          <div className="panel-title">
            <span className="panel-icon-wrapper">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </span>
            Conversation
          </div>
          {chatPanelElement}
        </section>

        {/* Right Workspace: Map of Understanding (40% - The Reflection Mirror) */}
        <section className="panel-container graph-panel-container">
          <div className="panel-title">
            <span className="panel-icon-wrapper">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
                <path d="M12 6v12M6 12h12"/>
              </svg>
            </span>
            Map of Understanding
          </div>
          {graphViewElement}
        </section>
      </main>

      {/* Secondary Insights Row: Centered Equal-Height Cards */}
      <section className="bottom-cards-grid">
        {discoveryCardElement}
        {questionsCardElement}
        {chapterDetailsElement}
      </section>

      {/* Bottom Full-Width Story of Understanding Timeline Section */}
      <section className="story-section">
        {storyOfUnderstandingElement}
      </section>
    </div>
  );
};