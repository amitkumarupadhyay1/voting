"""
Visual verification script for Task 4.4: Voting Timeline
Creates a standalone visualization to verify the chart looks correct
"""

import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime


def create_timeline_visualization():
    """Create the voting timeline visualization"""
    
    print("="*70)
    print("VOTING TIMELINE VISUAL VERIFICATION")
    print("="*70 + "\n")
    
    # Connect to database
    conn = sqlite3.connect('school_voting.db')
    
    # Fetch vote timestamps
    vote_timestamps = conn.execute('''
        SELECT created_at
        FROM votes
        ORDER BY created_at
    ''').fetchall()
    
    conn.close()
    
    if not vote_timestamps or len(vote_timestamps) == 0:
        print("⚠ No votes in database. Cannot create visualization.")
        print("Run test_task_4_4_verification.py first to create sample data.")
        return False
    
    print(f"✓ Found {len(vote_timestamps)} votes in database\n")
    
    # Parse timestamps and group by hour
    timestamps = [row[0] for row in vote_timestamps]
    df_votes = pd.DataFrame({'timestamp': timestamps})
    
    df_votes['datetime'] = pd.to_datetime(df_votes['timestamp'])
    df_votes['date_hour'] = df_votes['datetime'].dt.strftime('%Y-%m-%d %H:00')
    
    hourly_counts = df_votes.groupby('date_hour').size().reset_index(name='votes')
    hourly_counts['datetime'] = pd.to_datetime(hourly_counts['date_hour'])
    hourly_counts = hourly_counts.sort_values('datetime')
    
    # Calculate metrics
    total_votes = len(vote_timestamps)
    hours_with_votes = len(hourly_counts)
    avg_votes_per_hour = total_votes / hours_with_votes if hours_with_votes > 0 else 0
    
    peak_hour_data = hourly_counts.loc[hourly_counts['votes'].idxmax()]
    peak_hour = peak_hour_data['date_hour']
    peak_votes = peak_hour_data['votes']
    
    print("METRICS:")
    print(f"  Total Votes: {total_votes}")
    print(f"  Hours with Votes: {hours_with_votes}")
    print(f"  Average Votes/Hour: {avg_votes_per_hour:.2f}")
    print(f"  Peak Hour: {pd.to_datetime(peak_hour).strftime('%I:%M %p')}")
    print(f"  Peak Votes: {peak_votes}\n")
    
    # Create visualization
    votes_count = hourly_counts['votes'].tolist()
    colors = ['#f59e0b' if v == peak_votes else '#6366f1' for v in votes_count]
    
    fig = go.Figure()
    
    # Add line trace
    fig.add_trace(go.Scatter(
        x=hourly_counts['datetime'],
        y=votes_count,
        mode='lines+markers',
        name='Votes',
        line=dict(color='#6366f1', width=3),
        marker=dict(
            size=10,
            color=colors,
            line=dict(color='rgba(255,255,255,0.3)', width=2)
        ),
        fill='tozeroy',
        fillcolor='rgba(99,102,241,0.1)',
        hovertemplate='<b>%{x|%I:%M %p, %b %d}</b><br>' +
                      'Votes: %{y}<br>' +
                      '<extra></extra>'
    ))
    
    # Add average line
    fig.add_hline(
        y=avg_votes_per_hour,
        line_dash="dash",
        line_color="#22c55e",
        annotation_text=f"Average: {avg_votes_per_hour:.1f} votes/hour",
        annotation_position="right",
        annotation_font_color="#22c55e"
    )
    
    fig.update_layout(
        title=dict(
            text='Voting Activity Over Time',
            font=dict(size=18, color='white', family='Inter')
        ),
        xaxis=dict(
            title='Time',
            gridcolor='rgba(255,255,255,0.1)',
            color='white',
            tickformat='%I:%M %p<br>%b %d'
        ),
        yaxis=dict(
            title='Number of Votes',
            gridcolor='rgba(255,255,255,0.1)',
            color='white'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', family='Inter'),
        height=450,
        margin=dict(l=60, r=40, t=80, b=60),
        hovermode='x unified',
        showlegend=False
    )
    
    # Save to HTML
    output_file = 'voting_timeline_preview.html'
    fig.write_html(output_file)
    
    print(f"✓ Visualization created successfully!")
    print(f"✓ Saved to: {output_file}")
    print(f"\nOpen {output_file} in your browser to preview the chart.\n")
    
    # Display hourly breakdown
    print("HOURLY BREAKDOWN:")
    print("-" * 70)
    print(f"{'Time':<20} {'Date':<15} {'Votes':<10} {'% of Total':<10}")
    print("-" * 70)
    
    for _, row in hourly_counts.iterrows():
        time_str = row['datetime'].strftime('%I:%M %p')
        date_str = row['datetime'].strftime('%b %d, %Y')
        votes = row['votes']
        pct = (votes / total_votes * 100)
        
        marker = " 🔥" if votes == peak_votes else ""
        print(f"{time_str:<20} {date_str:<15} {votes:<10} {pct:<10.1f}{marker}")
    
    print("-" * 70)
    print("\n✅ Visual verification complete!")
    
    return True


if __name__ == '__main__':
    try:
        success = create_timeline_visualization()
        
        if success:
            print("\n" + "="*70)
            print("NEXT STEPS")
            print("="*70)
            print("\n1. Open 'voting_timeline_preview.html' in your browser")
            print("2. Verify the chart displays correctly:")
            print("   - Line chart with blue line and markers")
            print("   - Peak hours highlighted in orange")
            print("   - Green dashed line showing average")
            print("   - Proper time formatting on X-axis")
            print("   - Vote counts on Y-axis")
            print("\n3. Run the Streamlit app to see it in context:")
            print("   streamlit run app.py")
            print("   Login as admin → Navigate to Analytics tab")
            print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
