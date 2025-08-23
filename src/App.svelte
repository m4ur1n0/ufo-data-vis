<script>
    import BarGraphs from './BarGraphs.svelte';
    import Home from './Home.svelte'
</script>

<main>
    <div id="main-vis-container">
        <Home />

        <BarGraphs />
    </div>
</main>

<style>
  main {
    display: flex;
    align-items: center;
    justify-content: center;

    width : 100vw;
    height : 100vh;

    top : 0;
    left : 0;

    /* padding-left : 20px;
    padding-right : 20px; */

    /* border : 2px solid white; */

    overflow-x: hidden;
  }

  #main-vis-container {

    display : flex;
    align-items: center;
    justify-content: center;

    width : 100%;
    height : 100%;

    gap : 25px;

  }
</style>
