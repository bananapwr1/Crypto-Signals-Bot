#!/usr/bin/env python3
"""
Анализатор данных для разработки безрисковой торговой стратегии
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json

class StrategyAnalyzer:
    def __init__(self, db_path='crypto_signals_bot.db'):
        self.conn = sqlite3.connect(db_path)
        
    def get_signal_performance_stats(self):
        """Статистика по performance сигналов из signal_performance"""
        query = """
        SELECT 
            asset,
            timeframe,
            total_signals,
            wins,
            losses,
            ROUND(CAST(wins AS FLOAT) / NULLIF(total_signals, 0) * 100, 2) as win_rate,
            adaptive_weight
        FROM signal_performance
        WHERE total_signals >= 5
        ORDER BY win_rate DESC
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_market_patterns(self):
        """Анализ паттернов из market_history"""
        query = """
        SELECT 
            asset_symbol,
            timeframe,
            trend,
            signal_generated,
            AVG(volatility) as avg_volatility,
            AVG(confidence) as avg_confidence,
            COUNT(*) as total_records,
            SUM(CASE WHEN whale_detected = 1 THEN 1 ELSE 0 END) as whale_count
        FROM market_history
        GROUP BY asset_symbol, timeframe, trend, signal_generated
        HAVING total_records >= 3
        ORDER BY avg_confidence DESC
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_timeframe_statistics(self):
        """Статистика по таймфреймам"""
        # Из signal_performance
        perf_query = """
        SELECT 
            timeframe,
            SUM(total_signals) as total_signals,
            SUM(wins) as total_wins,
            SUM(losses) as total_losses,
            ROUND(CAST(SUM(wins) AS FLOAT) / NULLIF(SUM(total_signals), 0) * 100, 2) as win_rate
        FROM signal_performance
        WHERE total_signals >= 5
        GROUP BY timeframe
        ORDER BY win_rate DESC
        """
        df_perf = pd.read_sql_query(perf_query, self.conn)
        
        # Из market_history
        market_query = """
        SELECT 
            timeframe,
            AVG(volatility) as avg_volatility,
            AVG(confidence) as avg_confidence,
            COUNT(*) as scan_count,
            SUM(CASE WHEN whale_detected = 1 THEN 1 ELSE 0 END) as whale_detections
        FROM market_history
        GROUP BY timeframe
        """
        df_market = pd.read_sql_query(market_query, self.conn)
        
        # Объединим данные
        df = pd.merge(df_perf, df_market, on='timeframe', how='outer')
        return df
    
    def get_directional_stats(self):
        """Статистика по направлениям (CALL/PUT)"""
        query = """
        SELECT 
            signal_generated as direction,
            trend,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence,
            AVG(volatility) as avg_volatility
        FROM market_history
        WHERE signal_generated IN ('CALL', 'PUT')
        GROUP BY signal_generated, trend
        ORDER BY count DESC
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_time_patterns(self):
        """Временные паттерны (лучшие часы для торговли)"""
        query = """
        SELECT 
            strftime('%H', timestamp) as hour,
            COUNT(*) as signal_count,
            AVG(confidence) as avg_confidence,
            AVG(volatility) as avg_volatility,
            SUM(CASE WHEN whale_detected = 1 THEN 1 ELSE 0 END) as whale_count
        FROM market_history
        GROUP BY hour
        ORDER BY hour
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_volatility_impact(self):
        """Влияние волатильности на результаты"""
        query = """
        SELECT 
            CASE 
                WHEN volatility < 0.3 THEN 'Low (< 0.3%)'
                WHEN volatility < 0.7 THEN 'Medium (0.3-0.7%)'
                WHEN volatility < 1.5 THEN 'High (0.7-1.5%)'
                ELSE 'Very High (> 1.5%)'
            END as volatility_range,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence,
            AVG(score) as avg_score
        FROM market_history
        GROUP BY volatility_range
        ORDER BY avg_confidence DESC
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_top_performers(self, limit=10):
        """Топ активов по win rate"""
        query = f"""
        SELECT 
            asset,
            timeframe,
            total_signals,
            wins,
            losses,
            ROUND(CAST(wins AS FLOAT) / total_signals * 100, 2) as win_rate,
            adaptive_weight
        FROM signal_performance
        WHERE total_signals >= 5
        ORDER BY win_rate DESC, total_signals DESC
        LIMIT {limit}
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_low_performers(self, limit=10):
        """Худшие активы по win rate"""
        query = f"""
        SELECT 
            asset,
            timeframe,
            total_signals,
            wins,
            losses,
            ROUND(CAST(wins AS FLOAT) / total_signals * 100, 2) as win_rate,
            adaptive_weight
        FROM signal_performance
        WHERE total_signals >= 5
        ORDER BY win_rate ASC, total_signals DESC
        LIMIT {limit}
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def analyze_whale_impact(self):
        """Анализ влияния активности китов"""
        query = """
        SELECT 
            whale_detected,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence,
            AVG(score) as avg_score,
            AVG(volatility) as avg_volatility
        FROM market_history
        GROUP BY whale_detected
        """
        df = pd.read_sql_query(query, self.conn)
        df['whale_status'] = df['whale_detected'].map({0: 'No Whales', 1: 'Whales Detected'})
        return df
    
    def generate_full_report(self):
        """Генерация полного отчета"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'top_performers': self.get_top_performers(10).to_dict('records'),
            'low_performers': self.get_low_performers(10).to_dict('records'),
            'timeframe_stats': self.get_timeframe_statistics().to_dict('records'),
            'directional_stats': self.get_directional_stats().to_dict('records'),
            'time_patterns': self.get_time_patterns().to_dict('records'),
            'volatility_impact': self.get_volatility_impact().to_dict('records'),
            'whale_impact': self.analyze_whale_impact().to_dict('records'),
            'market_patterns': self.get_market_patterns().head(20).to_dict('records')
        }
        return report
    
    def print_summary(self):
        """Вывести краткую статистику"""
        print("=" * 80)
        print("📊 СТАТИСТИЧЕСКИЙ АНАЛИЗ ТОРГОВЫХ СИГНАЛОВ")
        print("=" * 80)
        
        # Топ активов
        print("\n🏆 ТОП-10 АКТИВОВ ПО WIN RATE (минимум 5 сигналов):")
        print("-" * 80)
        top = self.get_top_performers(10)
        if not top.empty:
            for idx, row in top.iterrows():
                print(f"{idx+1:2d}. {row['asset']:12s} {row['timeframe']:3s} | "
                      f"Win Rate: {row['win_rate']:5.1f}% | "
                      f"Signals: {int(row['total_signals']):3d} | "
                      f"W/L: {int(row['wins'])}/{int(row['losses'])}")
        else:
            print("   Недостаточно данных (нужно минимум 5 завершенных сигналов)")
        
        # Статистика по таймфреймам
        print("\n⏱️  СТАТИСТИКА ПО ТАЙМФРЕЙМАМ:")
        print("-" * 80)
        tf_stats = self.get_timeframe_statistics()
        for idx, row in tf_stats.iterrows():
            print(f"{row['timeframe']:3s} | ", end='')
            if pd.notna(row.get('win_rate')):
                print(f"Win Rate: {row['win_rate']:5.1f}% | Signals: {int(row['total_signals']):4d} | ", end='')
            print(f"Avg Vol: {row['avg_volatility']:.2f}% | Avg Conf: {row['avg_confidence']:.1f}%")
        
        # Волатильность
        print("\n📈 ВЛИЯНИЕ ВОЛАТИЛЬНОСТИ:")
        print("-" * 80)
        vol_impact = self.get_volatility_impact()
        for idx, row in vol_impact.iterrows():
            print(f"{row['volatility_range']:20s} | "
                  f"Count: {int(row['count']):4d} | "
                  f"Avg Conf: {row['avg_confidence']:.1f}% | "
                  f"Avg Score: {row['avg_score']:.1f}")
        
        # Киты
        print("\n🐋 ВЛИЯНИЕ КИТОВ:")
        print("-" * 80)
        whale = self.analyze_whale_impact()
        for idx, row in whale.iterrows():
            print(f"{row['whale_status']:20s} | "
                  f"Count: {int(row['count']):4d} | "
                  f"Avg Conf: {row['avg_confidence']:.1f}% | "
                  f"Avg Vol: {row['avg_volatility']:.2f}%")
        
        # Временные паттерны
        print("\n🕐 ВРЕМЕННЫЕ ПАТТЕРНЫ (по часам UTC):")
        print("-" * 80)
        time_patterns = self.get_time_patterns()
        for idx, row in time_patterns.iterrows():
            hour = int(row['hour'])
            print(f"{hour:02d}:00 | "
                  f"Signals: {int(row['signal_count']):4d} | "
                  f"Avg Conf: {row['avg_confidence']:.1f}% | "
                  f"Whales: {int(row['whale_count']):3d}")
        
        print("\n" + "=" * 80)
    
    def close(self):
        self.conn.close()

if __name__ == "__main__":
    analyzer = StrategyAnalyzer()
    analyzer.print_summary()
    
    # Сохранить полный отчет в JSON
    report = analyzer.generate_full_report()
    with open('strategy_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("\n✅ Полный отчет сохранен в strategy_analysis_report.json")
    
    analyzer.close()
