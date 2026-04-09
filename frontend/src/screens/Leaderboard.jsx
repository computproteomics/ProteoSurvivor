import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLeaderboard } from '../api/client';
import useGameStore from '../store/gameSlice';
import styles from './Leaderboard.module.css';

function scoreValue(score) {
  return typeof score === 'number' ? score : Number.NEGATIVE_INFINITY;
}

function sortEntries(entries) {
  return [...entries].sort((left, right) => {
    const scoreDelta = scoreValue(right.score) - scoreValue(left.score);
    if (scoreDelta !== 0) {
      return scoreDelta;
    }
    return (left.user_name || left.user_id).localeCompare(right.user_name || right.user_id);
  });
}

function formatScore(score) {
  if (typeof score !== 'number') {
    return 'No score yet';
  }
  return score.toFixed(Number.isInteger(score) ? 0 : 2);
}

function LeaderboardTable({ title, badgeClassName, entries, currentUserId }) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <h2 className={styles.sectionTitle}>{title}</h2>
        <span className={`${styles.sectionBadge} ${badgeClassName}`}>{entries.length}</span>
      </div>

      {entries.length === 0 ? (
        <div className={styles.emptyState}>No players in this section yet.</div>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Player</th>
                <th>Last Station</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => {
                const isCurrentUser = currentUserId && entry.user_id === currentUserId;
                return (
                  <tr
                    key={`${entry.user_id}-${entry.status}`}
                    className={isCurrentUser ? styles.currentUserRow : ''}
                  >
                    <td>{index + 1}</td>
                    <td>
                      <div className={styles.playerCell}>
                        <span className={styles.playerName}>{entry.user_name}</span>
                        {isCurrentUser && <span className={styles.youBadge}>You</span>}
                      </div>
                    </td>
                    <td>{entry.last_station_id || 'No runs yet'}</td>
                    <td>{formatScore(entry.score)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function Leaderboard() {
  const navigate = useNavigate();
  const userId = useGameStore((state) => state.userId);

  const [leaderboard, setLeaderboard] = useState({ finished: [], dnf: [], current_user_result: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function loadLeaderboard() {
      setLoading(true);
      setError('');

      try {
        const { data } = await getLeaderboard();
        if (!cancelled) {
          setLeaderboard({
            finished: Array.isArray(data.finished) ? data.finished : [],
            dnf: Array.isArray(data.dnf) ? data.dnf : [],
            current_user_result: data.current_user_result ?? null,
          });
        }
      } catch {
        if (!cancelled) {
          setError('Could not load the leaderboard right now.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadLeaderboard();

    return () => {
      cancelled = true;
    };
  }, []);

  const finishedEntries = useMemo(() => sortEntries(leaderboard.finished), [leaderboard.finished]);
  const dnfEntries = useMemo(() => sortEntries(leaderboard.dnf), [leaderboard.dnf]);
  const displayedUserIds = useMemo(
    () => new Set([...finishedEntries, ...dnfEntries].map((entry) => entry.user_id)),
    [finishedEntries, dnfEntries]
  );

  const currentUserResult = leaderboard.current_user_result;
  const showCurrentUserCard = Boolean(
    currentUserResult && currentUserResult.user_id === userId && !displayedUserIds.has(userId)
  );

  return (
    <div className={styles.page}>
      <div className={styles.shell}>
        <div className={styles.hero}>
          <div>
            <p className={styles.kicker}>Live ranking</p>
            <h1 className={styles.title}>Leaderboard</h1>
            <p className={styles.subtitle}>
              Finished runs stay on top. Everyone else is listed below as DNF until they reach Veit.
            </p>
          </div>

          <button className={styles.backButton} onClick={() => navigate('/world')}>
            Back to map
          </button>
        </div>

        {loading ? <div className={styles.messageCard}>Loading leaderboard...</div> : null}
        {error ? <div className={styles.errorCard}>{error}</div> : null}

        {!loading && !error ? (
          <>
            {showCurrentUserCard ? (
              <section className={styles.currentUserCard}>
                <p className={styles.currentUserLabel}>Your current result</p>
                <div className={styles.currentUserGrid}>
                  <div>
                    <span className={styles.cardKey}>Player</span>
                    <strong>{currentUserResult.user_name}</strong>
                  </div>
                  <div>
                    <span className={styles.cardKey}>Status</span>
                    <strong>{currentUserResult.status}</strong>
                  </div>
                  <div>
                    <span className={styles.cardKey}>Last station</span>
                    <strong>{currentUserResult.last_station_id || 'No runs yet'}</strong>
                  </div>
                  <div>
                    <span className={styles.cardKey}>Score</span>
                    <strong>{formatScore(currentUserResult.score)}</strong>
                  </div>
                </div>
              </section>
            ) : null}

            <div className={styles.grid}>
              <LeaderboardTable
                title="Finished"
                badgeClassName={styles.finishedBadge}
                entries={finishedEntries}
                currentUserId={userId}
              />
              <LeaderboardTable
                title="DNF"
                badgeClassName={styles.dnfBadge}
                entries={dnfEntries}
                currentUserId={userId}
              />
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}