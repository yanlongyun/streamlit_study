import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# 页面设置
st.set_page_config(
    page_title="滞销库存分析仪表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .positive-change {
        color: #00cc96;
    }
    .negative-change {
        color: #ef553b;
    }
</style>
""", unsafe_allow_html=True)


def load_data(uploaded_file):
    """加载并处理数据"""
    try:
        df = pd.read_csv(uploaded_file)

        # 数据清洗和预处理
        required_columns = ['店铺', '品名', '产品类别', 'Msku', '日均', '上月滞销', '本月滞销']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"数据文件中缺少必要列: {col}")
                return None

        # 转换数值列
        numeric_columns = ['日均', '上月滞销', '本月滞销']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 计算滞销数量变化
        df['滞销数量变化'] = df['本月滞销'] - df['上月滞销']
        df['变化百分比'] = (df['滞销数量变化'] / df['上月滞销'].replace(0, 1)) * 100

        return df
    except Exception as e:
        st.error(f"数据加载失败: {str(e)}")
        return None


def create_summary_metrics(df):
    """创建汇总指标"""
    col1, col2, col3, col4 = st.columns(4)

    total_current = df['本月滞销'].sum()
    total_previous = df['上月滞销'].sum()
    total_change = total_current - total_previous
    change_percentage = (total_change / total_previous * 100) if total_previous > 0 else 0

    with col1:
        st.metric(
            label="本月总滞销数量",
            value=f"{total_current:,.0f}",
            delta=f"{total_change:+,.0f} ({change_percentage:+.1f}%)"
        )

    with col2:
        avg_daily = df['日均'].mean()
        st.metric(
            label="平均日均销量",
            value=f"{avg_daily:.1f}"
        )

    with col3:
        products_count = df['品名'].nunique()
        st.metric(
            label="滞销产品数量",
            value=f"{products_count:,}"
        )

    with col4:
        stores_count = df['店铺'].nunique()
        st.metric(
            label="涉及店铺数量",
            value=f"{stores_count:,}"
        )


def create_trend_chart(df, group_by='产品类别'):
    """创建滞销趋势图表"""
    if group_by == '日期':
        # 如果有日期数据，按日期分组
        trend_data = df.groupby('日期').agg({
            '上月滞销': 'sum',
            '本月滞销': 'sum'
        }).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend_data['日期'], y=trend_data['上月滞销'],
                                 name='上月滞销', line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=trend_data['日期'], y=trend_data['本月滞销'],
                                 name='本月滞销', line=dict(color='red')))

    else:
        # 按其他维度分组
        trend_data = df.groupby(group_by).agg({
            '上月滞销': 'sum',
            '本月滞销': 'sum'
        }).reset_index()

        fig = go.Figure(data=[
            go.Bar(name='上月滞销', x=trend_data[group_by], y=trend_data['上月滞销']),
            go.Bar(name='本月滞销', x=trend_data[group_by], y=trend_data['本月滞销'])
        ])

    fig.update_layout(
        title=f'按{group_by}分组的滞销趋势对比',
        xaxis_title=group_by,
        yaxis_title='滞销数量',
        barmode='group',
        height=400
    )

    return fig


def create_comparison_chart(df):
    """创建对比分析图表"""
    # 滞销变化分布
    fig1 = px.histogram(df, x='滞销数量变化',
                        title='滞销数量变化分布',
                        labels={'滞销数量变化': '滞销数量变化量'})
    fig1.update_layout(height=300)

    # 店铺滞销排名
    store_data = df.groupby('店铺').agg({
        '本月滞销': 'sum',
        '滞销数量变化': 'sum'
    }).reset_index().sort_values('本月滞销', ascending=False).head(10)

    fig2 = px.bar(store_data, x='店铺', y='本月滞销',
                  title='店铺滞销数量TOP10',
                  color='滞销数量变化',
                  color_continuous_scale='RdYlGn_r')
    fig2.update_layout(height=300)

    return fig1, fig2


def main():
    # 标题
    st.markdown('<div class="main-header">📊 滞销库存统计及对比分析仪表板</div>',
                unsafe_allow_html=True)

    # 文件上传
    uploaded_file = st.sidebar.file_uploader(
        "上传CSV文件",
        type=['csv'],
        help="请上传包含店铺、品名、产品类别、Msku、日均、上月滞销、本月滞销等字段的CSV文件"
    )

    if uploaded_file is not None:
        # 加载数据
        df = load_data(uploaded_file)

        if df is not None:
            # 侧边栏筛选器
            st.sidebar.header("数据筛选")

            # 店铺筛选
            stores = ['全部'] + sorted(df['店铺'].unique().tolist())
            selected_store = st.sidebar.selectbox('选择店铺', stores)

            # 产品类别筛选
            categories = ['全部'] + sorted(df['产品类别'].unique().tolist())
            selected_category = st.sidebar.selectbox('选择产品类别', categories)

            # 日期筛选（如果存在日期列）
            date_columns = [col for col in df.columns if '日期' in col or 'date' in col.lower()]
            if date_columns:
                date_column = date_columns[0]
                min_date = df[date_column].min()
                max_date = df[date_column].max()
                selected_dates = st.sidebar.date_input(
                    "选择日期范围",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )

            # 应用筛选
            filtered_df = df.copy()
            if selected_store != '全部':
                filtered_df = filtered_df[filtered_df['店铺'] == selected_store]
            if selected_category != '全部':
                filtered_df = filtered_df[filtered_df['产品类别'] == selected_category]

            # 显示汇总指标
            st.header("📈 数据概览")
            create_summary_metrics(filtered_df)

            # 滞销趋势分析
            st.header("📊 滞销趋势分析")

            col1, col2 = st.columns(2)

            with col1:
                group_by_option = st.selectbox(
                    "选择分组维度",
                    ['产品类别', '店铺', '日期'] if '日期' in df.columns else ['产品类别', '店铺']
                )
                trend_fig = create_trend_chart(filtered_df, group_by_option)
                st.plotly_chart(trend_fig, use_container_width=True)

            with col2:
                # 滞销产品TOP10
                top_products = filtered_df.nlargest(10, '本月滞销')[['品名', '本月滞销', '滞销数量变化']]
                fig_top = px.bar(top_products, x='品名', y='本月滞销',
                                 title='滞销产品TOP10',
                                 color='滞销数量变化',
                                 color_continuous_scale='RdYlGn_r')
                fig_top.update_layout(height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig_top, use_container_width=True)

            # 对比分析
            st.header("🔍 对比分析")
            fig1, fig2 = create_comparison_chart(filtered_df)

            col3, col4 = st.columns(2)
            with col3:
                st.plotly_chart(fig1, use_container_width=True)
            with col4:
                st.plotly_chart(fig2, use_container_width=True)

            # 数据表格
            st.header("📋 详细数据")

            # 数据筛选选项
            col5, col6 = st.columns(2)
            with col5:
                show_columns = st.multiselect(
                    "选择显示列",
                    options=filtered_df.columns.tolist(),
                    default=['店铺', '品名', '产品类别', '本月滞销', '滞销数量变化', '变化百分比']
                )

            with col6:
                sort_by = st.selectbox("排序方式", options=filtered_df.columns.tolist())
                sort_order = st.radio("排序顺序", ["降序", "升序"], horizontal=True)

            # 应用排序
            display_df = filtered_df[show_columns] if show_columns else filtered_df
            display_df = display_df.sort_values(
                sort_by,
                ascending=(sort_order == "升序")
            )

            st.dataframe(display_df, use_container_width=True)

            # 数据导出
            st.header("📤 数据导出")

            col7, col8 = st.columns(2)

            with col7:
                # 导出筛选后的数据
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="导出筛选数据为CSV",
                    data=csv,
                    file_name=f"滞销分析数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

            with col8:
                # 生成分析报告
                if st.button("生成分析报告"):
                    report_text = f"""
滞销库存分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

总体情况:
- 本月总滞销数量: {filtered_df['本月滞销'].sum():,.0f}
- 上月总滞销数量: {filtered_df['上月滞销'].sum():,.0f}
- 滞销变化: {filtered_df['滞销数量变化'].sum():+,.0f}
- 平均日均销量: {filtered_df['日均'].mean():.1f}

涉及范围:
- 产品数量: {filtered_df['品名'].nunique():,}
- 店铺数量: {filtered_df['店铺'].nunique():,}
- 产品类别: {filtered_df['产品类别'].nunique():,}

滞销最严重的产品:
{filtered_df.nlargest(5, '本月滞销')[['品名', '本月滞销']].to_string(index=False)}
"""
                    st.text_area("分析报告", report_text, height=300)

        else:
            st.error("数据加载失败，请检查文件格式和内容")

    else:
        # 显示使用说明
        st.info("👈 请在侧边栏上传CSV文件开始分析")

        # 显示示例数据结构
        st.header("📝 数据格式要求")
        example_data = pd.DataFrame({
            '店铺': ['店铺A', '店铺A', '店铺B', '店铺B'],
            '品名': ['产品A', '产品B', '产品A', '产品C'],
            '产品类别': ['类别1', '类别2', '类别1', '类别3'],
            'Msku': ['MSKU001', 'MSKU002', 'MSKU001', 'MSKU003'],
            '日均': [10, 5, 8, 3],
            '上月滞销': [100, 50, 80, 30],
            '本月滞销': [120, 40, 90, 25]
        })
        st.dataframe(example_data)

        st.markdown("""
        ### 必要数据列:
        - **店铺**: 店铺名称
        - **品名**: 产品名称  
        - **产品类别**: 产品分类
        - **Msku**: 产品SKU
        - **日均**: 日均销量
        - **上月滞销**: 上月滞销数量
        - **本月滞销**: 本月滞销数量

        ### 可选数据列:
        - **日期**: 如果有时间序列数据
        """)


if __name__ == "__main__":
    main()